import unittest
import hashlib
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from temporal_learning.__main__ import main, replay, run, verify
from temporal_learning.config import canonical_json


class TemporalLearningCliTests(unittest.TestCase):
    def test_bad_run_id_is_rejected_before_creation(self):
        with patch("sys.stderr", new_callable=StringIO):
            self.assertEqual(main(["run", "--config", "experiments/temporal_learning_v1.json", "--run-id", "CON"]), 2)

    def test_verify_rejects_tampered_evidence(self):
        tiny = {"protocol": "temporal-learning-v1", "seeds": [0], "train_episodes": 1,
                "evaluation_episodes": 1, "checkpoints": [0, 1], "models": ["counts"],
                "horizon": 30, "context_tokens": 2, "laplace": 1, "scalar_decay": .8,
                "scalar_rate": .2, "try_penalty": .1, "tie_tolerance": 1e-12,
                "effect_threshold": .02, "positive_seed_minimum": 1, "time_limit_seconds": 60}
        config_hash = hashlib.sha256(canonical_json(tiny).encode("utf-8")).hexdigest()
        with TemporaryDirectory() as directory, patch("temporal_learning.__main__.load_config", return_value=(tiny, config_hash)):
            base = Path(directory)
            self.assertEqual(run("ignored", "e2e", base), 0)
            self.assertEqual(verify("e2e", base), 0)
            self.assertEqual(replay("e2e", base), 0)
            (base / "e2e" / "episodes.jsonl").write_text("{}\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                verify("e2e", base)

    def test_replay_rejects_checkpoint_tamper_even_with_updated_hash(self):
        tiny = {"protocol": "temporal-learning-v1", "seeds": [0], "train_episodes": 1,
                "evaluation_episodes": 1, "checkpoints": [0, 1], "models": ["counts"],
                "horizon": 30, "context_tokens": 2, "laplace": 1, "scalar_decay": .8,
                "scalar_rate": .2, "try_penalty": .1, "tie_tolerance": 1e-12,
                "effect_threshold": .02, "positive_seed_minimum": 1, "time_limit_seconds": 60}
        config_hash = hashlib.sha256(canonical_json(tiny).encode("utf-8")).hexdigest()
        with TemporaryDirectory() as directory, patch("temporal_learning.__main__.load_config", return_value=(tiny, config_hash)):
            base = Path(directory)
            self.assertEqual(run("ignored", "checkpoint", base), 0)
            checkpoint_path = base / "checkpoint" / "checkpoints.json"
            data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            data["0"]["1"]["counts"]["counts"]["bos/bos/try/ts"] += 1
            checkpoint_path.write_text(canonical_json(data), encoding="utf-8")
            completion_path = base / "checkpoint" / "completion.json"
            completion = json.loads(completion_path.read_text(encoding="utf-8"))
            completion["file_hashes"]["checkpoints.json"] = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
            completion_path.write_text(canonical_json(completion), encoding="utf-8")
            self.assertEqual(verify("checkpoint", base), 0)
            with self.assertRaises(ValueError):
                replay("checkpoint", base)

    def test_timeout_writes_failure_evidence(self):
        tiny = {"protocol": "temporal-learning-v1", "seeds": [0], "train_episodes": 1,
                "evaluation_episodes": 1, "checkpoints": [0, 1], "models": ["counts"],
                "horizon": 30, "context_tokens": 2, "laplace": 1, "scalar_decay": .8,
                "scalar_rate": .2, "try_penalty": .1, "tie_tolerance": 1e-12,
                "effect_threshold": .02, "positive_seed_minimum": 1, "time_limit_seconds": 1}
        with TemporaryDirectory() as directory, patch("temporal_learning.__main__.load_config", return_value=(tiny, "test-config")), patch("temporal_learning.__main__.time.monotonic", side_effect=(0.0, 2.0)):
            base = Path(directory)
            with self.assertRaises(TimeoutError):
                run("ignored", "timeout", base)
            failure = (base / "timeout" / "failure.json").read_text(encoding="utf-8")
            self.assertIn("TimeoutError", failure)
