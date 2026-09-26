from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from temporal_learning_followup.checks import derive_checks
from temporal_learning_followup.config import load_config
from temporal_learning_followup.preflight import preflight
from temporal_learning_followup.runner import run_full
from temporal_learning_followup.verify import replay_artifact, verify_artifact, verify_audit


def config() -> dict:
    return {"protocol": "temporal-learning-followup-1", "seeds": [20, 21], "train_episodes": 1,
            "evaluation_episodes": 1, "horizon": 30, "checkpoints": [0, 1],
            "models": ["counts", "affect", "failure_trace", "affect_neutral"], "context_tokens": 2,
            "laplace": 1, "scalar_decay": .8, "scalar_rate": .2, "try_penalty": .1,
            "tie_tolerance": 1e-12, "effect_threshold": .02, "positive_seed_minimum": 1,
            "time_limit_seconds": 60, "training_condition": "train", "held_out_condition": "failure_rich"}


class FollowupTests(unittest.TestCase):
    def test_followup2_strict_audit_and_replay_reject_self_rehashed_public_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"; value = config(); value["protocol"] = "temporal-learning-followup-2"
            self.assertEqual(run_full(value, root), 0)
            self.assertEqual(verify_audit(root), 0)
            self.assertEqual(replay_artifact(root), 0)
            path = root / "public" / "episodes.jsonl"
            rows = path.read_text(encoding="utf-8").splitlines(); row = json.loads(rows[0]); row["feedback"]["reward"] = 0.1
            rows[0] = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")); path.write_text("\n".join(rows) + "\n", encoding="utf-8")
            completion_path = root / "public" / "completion.json"; completion = json.loads(completion_path.read_text(encoding="utf-8"))
            completion["public_hashes"]["episodes.jsonl"] = hashlib.sha256(path.read_bytes()).hexdigest()
            completion_path.write_text(json.dumps(completion, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            with self.assertRaises(ValueError): verify_artifact(root)

    def test_preflight_reports_final_checkpoint_work_without_effect_claim(self):
        result = preflight(config())
        self.assertEqual(result["schema"], "temporal-learning-followup-1-preflight-1")
        self.assertEqual(result["training_rows"], 60)
        self.assertEqual(result["final_evaluation_rows"], 240)
        self.assertEqual(result["public_episode_rows"], 300)
        self.assertEqual(result["checkpoint_snapshots_per_seed"], 2)

    def test_config_rejects_v2_protocol(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"; value = config(); value["protocol"] = "temporal-learning-v2"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(ValueError): load_config(path)

    def test_isolated_e2e_and_read_only_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            self.assertEqual(run_full(config(), root), 0)
            self.assertEqual(verify_artifact(root), 0)
            public = root / "public"
            scores = json.loads((public / "metrics.json").read_text(encoding="utf-8"))["scores"]
            checks = json.loads((public / "checks.json").read_text(encoding="utf-8"))
            self.assertEqual(checks, derive_checks(config(), scores))
            self.assertEqual(set(checks["comparisons"]), {"affect_minus_counts", "affect_minus_failure_trace", "affect_minus_affect_neutral"})

    def test_verifier_rejects_self_inconsistent_public_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"; run_full(config(), root)
            episode_file = root / "public" / "episodes.jsonl"
            episode_file.write_text(episode_file.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaises(ValueError): verify_artifact(root)
