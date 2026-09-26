import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from temporal_learning_v2.checks import derive_checks, render_report
from temporal_learning_v2.diagnostics import safety_evidence
from temporal_learning_v2.evidence import canonical_public_line
from temporal_learning_v2.identity import source_hashes
from temporal_learning_v2.episode import run_public_episode, training_action
from temporal_learning_v2.stream import PublicJsonlWriter, RestrictedAuditJsonlWriter
from temporal_learning.learner import TemporalLearner
from temporal_learning_v2.runner import run_full, run_tiny
from temporal_learning_v2.verify import replay_full, replay_tiny, verify_full, verify_full_audit, verify_tiny, verify_tiny_audit


def config():
    return {"seeds": [0, 1], "train_episodes": 2, "effect_threshold": .02, "positive_seed_minimum": 2}


def scores():
    return {
        "0": {split: {"affect": [0.0, 0.0]} for split in ("test_A", "test_B")},
        "2": {split: {"affect": [.03, .04], "counts": [0.0, 0.0], "failure_trace": [0.0, 0.0]} for split in ("test_A", "test_B")},
    }


class TemporalLearningV2ChecksTests(unittest.TestCase):
    def test_paired_pre_registered_checks_and_rendering(self):
        checks = derive_checks(config(), scores(), persistence=True, safety=True)
        self.assertEqual(checks["L"]["test_A"]["status"], "pass")
        self.assertEqual(checks["S"]["test_B:affect_minus_counts"]["status"], "pass")
        self.assertEqual(checks["persistence"]["status"], "pass")
        self.assertIn("test_A:affect_minus_counts: pass", render_report(checks))

    def test_missing_or_misaligned_scores_are_not_assessed(self):
        broken = scores()
        broken["2"]["test_A"]["counts"] = [0.0]
        checks = derive_checks(config(), broken, persistence=None, safety=False)
        self.assertEqual(checks["L"]["test_A"]["status"], "not_assessed")
        self.assertEqual(checks["safety"]["status"], "fail")

    def test_non_finite_or_boolean_scores_are_not_assessed(self):
        for invalid in (float("nan"), float("inf"), True, "0.1"):
            with self.subTest(invalid=invalid):
                broken = scores()
                broken["2"]["test_A"]["counts"][0] = invalid
                checks = derive_checks(config(), broken, persistence=None, safety=None)
                self.assertEqual(checks["L"]["test_A"]["status"], "not_assessed")
        checks = derive_checks(config(), scores(), persistence=None, safety=None)
        self.assertEqual(checks["brier"]["status"], "not_assessed")

    def test_public_evidence_rejects_hidden_audit_or_tape(self):
        self.assertEqual(canonical_public_line({"action": "try", "feedback": {"reward": 1.0}}),
                         '{"action":"try","feedback":{"reward":1.0}}\n')
        for row in ({"audit": {"state": "G"}}, {"feedback": {"u": .5}}, {"state": "B"}):
            with self.subTest(row=row), self.assertRaises(ValueError):
                canonical_public_line(row)

    def test_identity_includes_environment_and_v2_sources(self):
        identity = source_hashes()
        self.assertIn("temporal_experience/environment.py", identity)
        self.assertIn("temporal_experience/random_tape.py", identity)
        self.assertIn("temporal_learning_v2/checks.py", identity)
        self.assertIn("temporal_learning/learner.py", identity)

    def test_v2_behavior_namespace_is_deterministic_and_distinct(self):
        self.assertEqual(training_action(1, 2, 3), training_action(1, 2, 3))

    def test_safety_evidence_runs_fail_closed_priority_cases(self):
        evidence = safety_evidence()
        self.assertTrue(evidence["passes"])
        self.assertEqual(evidence["test"]["case_count"], 5)
        self.assertEqual(set(evidence["allowlisted_actions"]), {"try", "safe", "recover"})

    def test_restricted_audit_is_separate_and_strict(self):
        with TemporaryDirectory() as directory:
            writer = RestrictedAuditJsonlWriter(Path(directory) / "audit.jsonl")
            writer.write({"phase":"training","seed":0,"checkpoint":None,"condition":"train","model":None,"episode":0,"step":0,"state_before":"G"})
            self.assertEqual(writer.close()["row_count"], 1)

    def test_public_episode_and_stream_do_not_emit_audit(self):
        rows = list(run_public_episode(TemporalLearner(), "train", 0, 0, learn_counts=True, behavior=True))
        self.assertEqual(len(rows), 30)
        self.assertEqual(rows[0]["remaining"], 30)
        self.assertTrue(rows[-1]["feedback"]["terminal"])
        with TemporaryDirectory() as directory:
            writer = PublicJsonlWriter(Path(directory) / "rows.jsonl")
            for row in rows:
                writer.write(row)
            receipt = writer.close()
        self.assertEqual(receipt["row_count"], 30)

    def test_tiny_run_writes_public_completion_without_audit(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "tiny"
            self.assertEqual(run_tiny({"seeds": [0]}, root), 0)
            self.assertTrue((root / "completion.json").is_file())
            self.assertFalse((root / "failure.json").exists())
            self.assertNotIn('"audit"', (root / "public" / "training.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(verify_tiny(root), 0)
            self.assertEqual(replay_tiny(root), 0)
            (root / "public" / "training.jsonl").write_text("{}\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                replay_tiny(root)

    def test_tiny_restricted_audit_is_committed_and_joined(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "tiny"
            run_tiny({"seeds": [0]}, root, with_restricted_audit=True)
            self.assertEqual(verify_tiny_audit(root), 0)

    def test_full_runner_writes_paired_metrics_checks_report_and_public_completion(self):
        full_config = {
            "protocol": "temporal-learning-v2", "seeds": [0, 1], "train_episodes": 1, "evaluation_episodes": 1,
            "horizon": 30, "checkpoints": [0, 1], "models": ["counts", "affect", "failure_trace"],
            "context_tokens": 2, "laplace": 1, "scalar_decay": .8, "scalar_rate": .2, "try_penalty": .1,
            "tie_tolerance": 1e-12, "effect_threshold": .02, "positive_seed_minimum": 2, "time_limit_seconds": 60,
        }
        with TemporaryDirectory() as directory:
            root = Path(directory) / "full"
            self.assertEqual(run_full(full_config, root, with_restricted_audit=True), 0)
            public = root / "public"
            self.assertTrue((public / "completion.json").is_file())
            self.assertFalse((root / "completion.json").exists())
            metrics = __import__("json").loads((public / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["seed_order"], [0, 1])
            self.assertEqual(set(metrics["scores"]["1"]["test_A"]), {"counts", "affect", "failure_trace"})
            self.assertIn("Synthetic functional-learning evidence only", (public / "report.md").read_text(encoding="utf-8"))
            self.assertEqual(verify_full(root), 0)
            self.assertEqual(verify_full_audit(root), 0)
            checks = json.loads((public / "checks.json").read_text(encoding="utf-8"))
            for name in ("brier", "context_try_samples", "neutral_diagnostic", "permuted_diagnostic"):
                self.assertEqual(checks[name]["status"], "pass")
            self.assertIn("## brier", (public / "report.md").read_text(encoding="utf-8"))
            self.assertEqual(replay_full(root), 0)
            current_diagnostics = (public / "diagnostics.json").read_bytes()
            current_checks = (public / "checks.json").read_bytes()
            current_report = (public / "report.md").read_bytes()
            current_completion = (public / "completion.json").read_bytes()
            legacy_diagnostics = json.loads(current_diagnostics)
            legacy_diagnostics.pop("learning")
            legacy_checks = derive_checks(full_config, metrics["scores"], persistence=True, safety=True)
            (public / "diagnostics.json").write_text(json.dumps(legacy_diagnostics, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            (public / "checks.json").write_text(json.dumps(legacy_checks, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            (public / "report.md").write_text(render_report(legacy_checks), encoding="utf-8", newline="\n")
            legacy_completion = json.loads(current_completion)
            for name in ("diagnostics.json", "checks.json", "report.md"):
                legacy_completion["public_hashes"][name] = hashlib.sha256((public / name).read_bytes()).hexdigest()
            (public / "completion.json").write_text(json.dumps(legacy_completion, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            self.assertEqual(verify_full(root), 0)
            self.assertEqual(replay_full(root), 0)
            (public / "diagnostics.json").write_bytes(current_diagnostics)
            (public / "checks.json").write_bytes(current_checks)
            (public / "report.md").write_bytes(current_report)
            (public / "completion.json").write_bytes(current_completion)
            self.assertEqual(verify_full(root), 0)
            manifest_path = public / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["source_hashes"]["temporal_learning_v2/verify.py"] = "0" * 64
            manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            completion = json.loads((public / "completion.json").read_text(encoding="utf-8"))
            completion["public_hashes"]["manifest.json"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            (public / "completion.json").write_text(json.dumps(completion, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            self.assertEqual(replay_full(root), 0)
            diagnostic_bytes = (public / "diagnostics.json").read_bytes()
            diagnostics = json.loads(diagnostic_bytes)
            diagnostics["learning"]["brier"]["sample_counts"]["0"]["same_distribution"]["counts"][0] += 1
            (public / "diagnostics.json").write_text(json.dumps(diagnostics, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            completion = json.loads((public / "completion.json").read_text(encoding="utf-8"))
            completion["public_hashes"]["diagnostics.json"] = hashlib.sha256((public / "diagnostics.json").read_bytes()).hexdigest()
            (public / "completion.json").write_text(json.dumps(completion, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_full(root)
            (public / "diagnostics.json").write_bytes(diagnostic_bytes)
            completion["public_hashes"]["diagnostics.json"] = hashlib.sha256(diagnostic_bytes).hexdigest()
            (public / "completion.json").write_text(json.dumps(completion, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            self.assertEqual(verify_full(root), 0)
            audit_path = root / "restricted_audit" / "audit.jsonl"
            audit_lines = audit_path.read_text(encoding="utf-8").splitlines()
            tampered_audit = json.loads(audit_lines[0])
            tampered_audit["seed"] = 99
            audit_lines[0] = json.dumps(tampered_audit, sort_keys=True, separators=(",", ":"))
            audit_path.write_text("\n".join(audit_lines) + "\n", encoding="utf-8")
            manifest_path = public / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["restricted_audit"]["sha256"] = hashlib.sha256(audit_path.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            completion = json.loads((public / "completion.json").read_text(encoding="utf-8"))
            completion["public_hashes"]["manifest.json"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            (public / "completion.json").write_text(json.dumps(completion, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_full_audit(root)
            with self.assertRaises(ValueError):
                replay_full(root)
            diagnostic_bytes = (public / "diagnostics.json").read_bytes()
            diagnostics = __import__("json").loads(diagnostic_bytes)
            diagnostics["safety"]["passes"] = False
            (public / "diagnostics.json").write_text(__import__("json").dumps(diagnostics, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            completion = __import__("json").loads((public / "completion.json").read_text(encoding="utf-8"))
            completion["public_hashes"]["diagnostics.json"] = __import__("hashlib").sha256((public / "diagnostics.json").read_bytes()).hexdigest()
            (public / "completion.json").write_text(__import__("json").dumps(completion, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_full(root)
            (public / "diagnostics.json").write_bytes(diagnostic_bytes)
            completion["public_hashes"]["diagnostics.json"] = __import__("hashlib").sha256(diagnostic_bytes).hexdigest()
            (public / "completion.json").write_text(__import__("json").dumps(completion, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            self.assertEqual(verify_full(root), 0)
            metrics["scores"]["1"]["test_A"]["affect"][0] += 1.0
            (public / "metrics.json").write_text(__import__("json").dumps(metrics, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            completion["public_hashes"]["metrics.json"] = __import__("hashlib").sha256((public / "metrics.json").read_bytes()).hexdigest()
            (public / "completion.json").write_text(__import__("json").dumps(completion, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_full(root)
