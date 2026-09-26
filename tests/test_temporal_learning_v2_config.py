import json
from io import StringIO
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from temporal_learning_v2.config import load_config
from temporal_learning_v2.__main__ import main
from temporal_learning_v2.preflight import preflight
from temporal_learning_v2.runner import run_full
from temporal_learning_v2.verify import replay_full, verify_full


def valid_config() -> dict:
    return {
        "protocol": "temporal-learning-v2", "seeds": [0], "train_episodes": 1,
        "evaluation_episodes": 1, "horizon": 30, "checkpoints": [0, 1],
        "models": ["counts", "affect", "failure_trace"], "context_tokens": 2,
        "laplace": 1, "scalar_decay": .8, "scalar_rate": .2, "try_penalty": .1,
        "tie_tolerance": 1e-12, "effect_threshold": .02,
        "positive_seed_minimum": 1, "time_limit_seconds": 60,
    }


def assert_utf8_no_bom(test_case: unittest.TestCase, path: Path) -> str:
    content = path.read_bytes()
    test_case.assertFalse(content.startswith(b"\xff\xfe"), path)
    test_case.assertFalse(content.startswith(b"\xfe\xff"), path)
    return content.decode("utf-8")


class TemporalLearningV2ConfigTests(unittest.TestCase):
    def test_pre_registered_config_and_hash(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(valid_config()), encoding="utf-8")
            config, digest = load_config(path)
        self.assertEqual(config["protocol"], "temporal-learning-v2")
        self.assertEqual(len(digest), 64)

    def test_rejects_unevaluable_seed_boundaries(self):
        for key, value in (("seeds", []), ("positive_seed_minimum", 2), ("effect_threshold", 0)):
            with self.subTest(key=key), TemporaryDirectory() as directory:
                config = valid_config()
                config[key] = value
                path = Path(directory) / "config.json"
                path.write_text(json.dumps(config), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_config(path)

    def test_isolated_cli_run_verify_and_replay(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "config.json"
            config_path.write_text(json.dumps(valid_config()), encoding="utf-8")
            output = root / "artifact"
            self.assertEqual(main(["run", "--config", str(config_path), "--output", str(output), "--with-audit"]), 0)
            self.assertEqual(main(["verify", "--output", str(output), "--with-audit"]), 0)
            self.assertEqual(main(["replay", "--output", str(output), "--with-audit"]), 0)

    def test_preflight_is_side_effect_free_and_counts_regular_work(self):
        regular = valid_config() | {"seeds": list(range(20)), "train_episodes": 600,
                                    "evaluation_episodes": 50, "checkpoints": [0, 100, 300, 600],
                                    "positive_seed_minimum": 12, "time_limit_seconds": 600}
        estimate = preflight(regular)
        self.assertEqual(estimate["training_rows"], 360_000)
        self.assertEqual(estimate["evaluation_rows"], 1_080_000)
        self.assertEqual(estimate["persistence_replay_rows"], 1_080_000)
        self.assertEqual(estimate["diagnostic_brier_rows"], 1_080_000)
        self.assertEqual(estimate["diagnostic_counterfactual_rows"], 1_080_000)
        self.assertEqual(estimate["diagnostic_rows"], 2_160_000)
        self.assertEqual(estimate["total_episode_rows"], 4_680_000)
        self.assertEqual(estimate["public_jsonl_byte_upper_bound"], 1_440_000 * 2_048)
        with TemporaryDirectory() as directory, patch("sys.stdout", new_callable=StringIO) as output:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(valid_config()), encoding="utf-8")
            self.assertEqual(main(["preflight", "--config", str(path)]), 0)
            self.assertEqual(json.loads(output.getvalue())["schema"], "temporal-learning-v2-preflight-2")
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_timeout_writes_failure_without_completion_and_verify_rejects_it(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "timeout"
            clock = iter((0.0, 2.0)).__next__
            with self.assertRaises(TimeoutError):
                run_full(valid_config() | {"time_limit_seconds": 1}, root, clock=clock)
            failure = json.loads((root / "failure.json").read_text(encoding="utf-8"))
            self.assertEqual(failure, {"status": "failed", "error_type": "TimeoutError", "stage": "training"})
            self.assertFalse((root / "public" / "completion.json").exists())
            with self.assertRaises(ValueError):
                verify_full(root)
            with self.assertRaises(ValueError):
                replay_full(root)

    def test_persistence_timeout_writes_finalization_failure_without_completion(self):
        calls = 0
        def clock() -> float:
            nonlocal calls
            calls += 1
            return 0.0 if calls <= 571 else 2.0
        with TemporaryDirectory() as directory:
            root = Path(directory) / "persistence-timeout"
            with self.assertRaises(TimeoutError):
                run_full(valid_config() | {"time_limit_seconds": 1}, root, clock=clock)
            failure = json.loads((root / "failure.json").read_text(encoding="utf-8"))
            self.assertEqual(failure, {"status": "failed", "error_type": "TimeoutError", "stage": "finalization"})
            self.assertFalse((root / "public" / "completion.json").exists())

    def test_v2_control_wrapper_creates_missing_parent_and_terminal_marker(self):
        workspace = Path(__file__).resolve().parents[1]
        script = workspace / "scripts" / "run_temporal_learning_v2_control.ps1"
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "config.json"
            config_path.write_text(json.dumps(valid_config()), encoding="utf-8")
            artifact = root / "nested" / "artifact"
            control = root / "nested" / "control"
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Mode", "run",
                 "-OutputDirectory", str(artifact), "-ControlDirectory", str(control),
                 "-ConfigPath", str(config_path), "-WithAudit"],
                capture_output=True, text=True, timeout=120, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            terminal = json.loads((control / "terminal.json").read_text(encoding="utf-8-sig"))
            self.assertEqual(terminal["mode"], "run")
            self.assertEqual(terminal["output_directory"], str(artifact))
            self.assertEqual(terminal["exit_code"], 0)
            self.assertTrue((artifact / "public" / "completion.json").is_file())
            self.assertTrue((control / "stdout.log").is_file())
            self.assertTrue((control / "stderr.log").is_file())
            assert_utf8_no_bom(self, control / "stdout.log")
            assert_utf8_no_bom(self, control / "stderr.log")
            assert_utf8_no_bom(self, control / "terminal.json")

    def test_v2_control_wrapper_records_failed_child_terminal_and_logs(self):
        workspace = Path(__file__).resolve().parents[1]
        script = workspace / "scripts" / "run_temporal_learning_v2_control.ps1"
        with TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "missing-artifact"
            control = root / "nested" / "control"
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Mode", "verify",
                 "-OutputDirectory", str(artifact), "-ControlDirectory", str(control)],
                capture_output=True, text=True, timeout=120, check=False)
            self.assertEqual(completed.returncode, 2, completed.stderr)
            terminal = json.loads((control / "terminal.json").read_text(encoding="utf-8"))
            self.assertEqual(terminal["mode"], "verify")
            self.assertEqual(terminal["output_directory"], str(artifact))
            self.assertEqual(terminal["exit_code"], 2)
            self.assertTrue((control / "stdout.log").is_file())
            stderr = assert_utf8_no_bom(self, control / "stderr.log")
            self.assertIn("temporal-learning-v2 error", stderr)
            self.assertNotIn("NativeCommandError", stderr)
            assert_utf8_no_bom(self, control / "stdout.log")
            assert_utf8_no_bom(self, control / "terminal.json")
            self.assertFalse(artifact.exists())

    def test_v2_control_wrapper_records_wrapper_error_after_control_creation(self):
        workspace = Path(__file__).resolve().parents[1]
        script = workspace / "scripts" / "run_temporal_learning_v2_control.ps1"
        with TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "missing-artifact"
            control = root / "nested" / "control"
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Mode", "run",
                 "-OutputDirectory", str(artifact), "-ControlDirectory", str(control)],
                capture_output=True, text=True, timeout=120, check=False)
            self.assertEqual(completed.returncode, 1, completed.stderr)
            terminal = json.loads(assert_utf8_no_bom(self, control / "terminal.json"))
            self.assertEqual(terminal["exit_code"], 1)
            self.assertIn("ConfigPath is required", assert_utf8_no_bom(self, control / "stderr.log"))
            assert_utf8_no_bom(self, control / "stdout.log")
            self.assertFalse(artifact.exists())

    def test_v2_launcher_requires_matching_terminal_for_success_and_child_failure(self):
        workspace = Path(__file__).resolve().parents[1]
        launcher = workspace / "scripts" / "invoke_temporal_learning_v2_control.ps1"
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "config.json"
            config_path.write_text(json.dumps(valid_config()), encoding="utf-8")
            artifact = root / "artifact"
            control = root / "nested" / "control"
            success = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(launcher), "-Mode", "run",
                 "-OutputDirectory", str(artifact), "-ControlDirectory", str(control), "-ConfigPath", str(config_path), "-WithAudit"],
                capture_output=True, text=True, timeout=120, check=False)
            self.assertEqual(success.returncode, 0, success.stderr)
            failed_control = root / "nested" / "failed-control"
            failed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(launcher), "-Mode", "verify",
                 "-OutputDirectory", str(root / "missing-artifact"), "-ControlDirectory", str(failed_control)],
                capture_output=True, text=True, timeout=120, check=False)
            self.assertEqual(failed.returncode, 2, failed.stderr)
            self.assertEqual(json.loads((failed_control / "terminal.json").read_text(encoding="utf-8"))["exit_code"], 2)

    def test_v2_launcher_fails_closed_when_wrapper_leaves_no_terminal_marker(self):
        workspace = Path(__file__).resolve().parents[1]
        launcher = workspace / "scripts" / "invoke_temporal_learning_v2_control.ps1"
        with TemporaryDirectory() as directory:
            root = Path(directory)
            control = root / "control"
            control.mkdir()
            failed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(launcher), "-Mode", "verify",
                 "-OutputDirectory", str(root / "missing-artifact"), "-ControlDirectory", str(control)],
                capture_output=True, text=True, timeout=120, check=False)
            self.assertEqual(failed.returncode, 1)
            self.assertIn("terminal marker is missing", failed.stderr)
