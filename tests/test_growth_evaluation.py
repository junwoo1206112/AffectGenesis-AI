from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from affect_growth.environment import make_dataset
from affect_growth.evaluation import (
    EXPECTED_CONFIG, canonical, checked_run_dir, digest, load_config,
    render_report, safety_sweep, score, state_probe, summarize,
    validate_evidence_metrics, verify_report,
)
from affect_growth.learner import Learner
from affect_growth.models import Feedback
from functional_affect.models import Action


class GrowthEvaluationTests(unittest.TestCase):
    def test_report_order_survives_canonical_json_roundtrip(self):
        metrics = {
            "protocol": "test", "safety": {"cases": 45, "violations": 0},
            "summary": {"growth_supported": False, "state_action_change_rate": 0.0,
                        "contrasts": {name: {metric: {"mean": 0.1} for metric in ("C", "A", "J")}
                                      for name in ("pre", "frozen", "memory")}},
        }
        evidence = "artifacts/affect_growth/roundtrip"
        original = render_report(metrics, evidence)
        restored = json.loads(canonical(metrics))
        self.assertNotEqual(list(metrics["summary"]["contrasts"]), list(restored["summary"]["contrasts"]))
        self.assertEqual(original, render_report(restored, evidence))
        self.assertLess(original.index("| pre |"), original.index("| frozen |"))
        self.assertLess(original.index("| frozen |"), original.index("| memory |"))

    def test_cli_run_verify_and_tampered_report_in_isolated_workspace(self):
        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(project / "src", root / "src", ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copyfile(project / "experiments" / "growth_v0_2.json", root / "config.json")
            env = {**os.environ, "PYTHONPATH": str(root / "src"), "PYTHONIOENCODING": "utf-8"}

            def cli(*args):
                return subprocess.run([sys.executable, "-m", "affect_growth", *args],
                                      cwd=root, env=env, capture_output=True, text=True,
                                      encoding="utf-8", timeout=120)

            execution = cli("--config", "config.json", "--run-id", "e2e")
            self.assertEqual(execution.returncode, 0, execution.stderr)
            report = root / "artifacts" / "affect_growth" / "e2e" / "report.md"
            verification = cli("--verify-report", str(report))
            self.assertEqual(verification.returncode, 0, verification.stderr)
            self.assertIn("REPORT VERIFIED", verification.stdout)
            # A human-facing copy must verify too, but a changed claim must not.
            copied = root / "report-copy.md"
            shutil.copyfile(report, copied)
            self.assertEqual(cli("--verify-report", str(copied)).returncode, 0)
            copied.write_text(copied.read_text(encoding="utf-8") + "modified claim\n", encoding="utf-8")
            self.assertNotEqual(cli("--verify-report", str(copied)).returncode, 0)

    def test_score_has_no_feedback_or_source_mutation(self):
        model = Learner()
        for case in make_dataset(0, "train"):
            model.learn(case.observation, case.feedback)
        before = canonical(model.to_dict("test"))
        cases = make_dataset(0, "test")
        result = score(model, cases)
        poisoned = [replace(case, feedback=Feedback(99, Action.SAFE_HANDOFF, 99)) for case in cases]
        self.assertEqual(result, score(model, poisoned))
        self.assertEqual(before, canonical(model.to_dict("test")))
        self.assertEqual(result["n"], 100)
        self.assertEqual(len(result["family_scores"]), 5)
        self.assertEqual(sum(map(sum, result["confusion"])), 100)

    def test_state_probe_is_deterministic_and_nonmutating(self):
        model = Learner()
        for case in make_dataset(1, "train"):
            model.learn(case.observation, case.feedback)
        before = canonical(model.to_dict("test"))
        first = state_probe(model, make_dataset(1, "dev"), 1)
        self.assertEqual(first, state_probe(model, make_dataset(1, "dev"), 1))
        self.assertEqual(before, canonical(model.to_dict("test")))
        self.assertEqual(first["n"], 100)

    def test_config_rejects_changes_unknowns_and_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            path.write_text(json.dumps(EXPECTED_CONFIG), encoding="utf-8")
            self.assertEqual(load_config(path), EXPECTED_CONFIG)
            for modified in ({**EXPECTED_CONFIG, "extra": 1}, {**EXPECTED_CONFIG, "alpha": 2}):
                path.write_text(json.dumps(modified), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_config(path)
            path.write_text('{"alpha":1,"alpha":2}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(path)

    def test_output_path_validation_and_overwrite_refusal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for bad in ("../escape", "", "a/b", "C:bad", "CON", "nul", "a.b", "x" * 65):
                with self.assertRaises(ValueError):
                    checked_run_dir(root, bad)
            target = checked_run_dir(root, "safe-001")
            target.mkdir(parents=True)
            with self.assertRaises(FileExistsError):
                checked_run_dir(root, "safe-001")

    def test_safety_sweep_has_zero_violations(self):
        self.assertEqual(safety_sweep(), {"cases": 45, "violations": 0})

    def test_report_rejects_missing_escaped_or_incomplete_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            report = root / "report.md"
            for text in ("fake report", "Evidence: ../../secret", "Evidence: artifacts/affect_growth/../secret"):
                report.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    verify_report(report, root)
            with self.assertRaises(ValueError):
                validate_evidence_metrics({"rows": []})

    def test_negative_research_result_is_reported_not_hidden(self):
        rows = []
        for seed in range(10):
            for mode in ("learned", "frozen", "memory"):
                for step in (0, 300):
                    for reset in (True, False):
                        rows.append({"seed": seed, "order": "chronological", "mode": mode,
                                     "step": step, "reset": reset, "C": 0.5, "A": 0.5, "J": 0.25})
        probes = [{"mode": "learned", "order": "chronological", "action_change_rate": {"neutral": 0.0}}]
        result = summarize(rows, probes)
        self.assertFalse(result["growth_supported"])
        self.assertFalse(result["state_influence_observed"])
        text = render_report({"protocol": "test", "safety": {"cases": 45, "violations": 0}, "summary": result},
                             "artifacts/affect_growth/test")
        self.assertIn("미지지/불충분", text)
        self.assertIn("주관적 감정", text)

    def test_hashes_are_stable_and_nonfinite_rejected(self):
        self.assertEqual(digest({"b": 2, "a": 1}), digest({"a": 1, "b": 2}))
        with self.assertRaises(ValueError):
            canonical({"value": float("nan")})


if __name__ == "__main__":
    unittest.main()
