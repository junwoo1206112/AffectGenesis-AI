import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from controllability_protocol.core import Action, Card, decide, mechanism_row
from controllability_protocol.calibrated import decide_calibrated, evaluate_isolated_kernel, summarize_calibrated_evidence
from controllability_protocol.calibrated_artifact import replay as calibrated_replay, run as calibrated_run, verify as calibrated_verify
from controllability_protocol.calibrated_family_artifact import replay as calibrated_family_replay, run as calibrated_family_run, verify as calibrated_family_verify
from controllability_protocol.evidence import run, verify
from controllability_protocol.probabilistic import replay, run as probabilistic_run, verify as probabilistic_verify
from controllability_protocol.provenance import verify_provenance, verify_reproduction_contract
from controllability_protocol.provenance import content_sha256, verify_calibrated_card_family, verify_calibrated_readiness, verify_distribution_gate, verify_external_intake, verify_external_review, verify_external_submission, verify_next_hypothesis_preregistration, verify_public_card_source_review, verify_reproduction_bundle
from controllability_protocol.__main__ import main


class ControllabilityProtocolTests(unittest.TestCase):
    def setUp(self):
        self.high = Card("holdout-high", "holdout", "high", True)
        self.low = Card("holdout-low", "holdout", "low", True)

    def test_single_public_intervention_changes_recover_choice(self):
        self.assertEqual(decide(self.high), (Action.RECOVER, "public_controllability_high"))
        self.assertEqual(decide(self.low), (Action.SAFE, "default_safe"))

    def test_permutation_and_ablation_are_explicit_controls(self):
        self.assertEqual(decide(self.high, permute_label=True)[0], Action.SAFE)
        self.assertEqual(decide(self.high, ablated=True)[0], Action.SAFE)

    def test_unrecoverable_and_safety_never_enable_recover(self):
        self.assertEqual(decide(Card("u", "holdout", "high", False))[0], Action.SAFE)
        self.assertEqual(decide(Card("s", "holdout", "high", True, safety_urgency=True))[0], Action.SAFE)
        self.assertEqual(decide(Card("b", "holdout", "high", True, boundary_risk=True))[0], Action.SAFE)

    def test_mechanism_log_exposes_input_intervention_rule_and_action(self):
        row = mechanism_row(self.high)
        self.assertEqual(set(row), {"card_id", "family", "controllability", "recoverable", "ablated", "permuted", "action", "rule", "reward"})
        self.assertEqual(row["action"], "recover")

    def test_registry_artifact_recomputes_controls(self):
        registry = Path(__file__).parents[1] / "experiments" / "controllability_cards.json"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "artifact"; self.assertEqual(run(registry, root), 0); self.assertEqual(verify(root), 0)

    def test_probabilistic_holdout_evidence_is_paired_and_replayable(self):
        base = Path(__file__).parents[1]
        protocol = base / "experiments" / "controllability_probabilistic_v1.json"
        registry = base / "experiments" / "controllability_cards.json"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "artifact"
            self.assertEqual(probabilistic_run(protocol, registry, root), 0)
            self.assertEqual(probabilistic_verify(root), 0)
            self.assertEqual(replay(root), 0)
            evidence = json.loads((root / "evidence.json").read_text(encoding="utf-8"))
            self.assertEqual(len(evidence["seed_rows"]), 20)
            self.assertTrue(evidence["criterion"]["passes"])
            self.assertTrue(evidence["criterion"]["controls_pass"])

    def test_probabilistic_verifier_rejects_changed_evidence(self):
        base = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "artifact"
            probabilistic_run(base / "experiments" / "controllability_probabilistic_v1.json", base / "experiments" / "controllability_cards.json", root)
            (root / "evidence.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                probabilistic_verify(root)

    def test_independent_cards_kernel_and_seeds_are_replayable_without_pooling(self):
        base = Path(__file__).parents[1]
        baseline = json.loads((base / "experiments" / "controllability_probabilistic_v1.json").read_text(encoding="utf-8"))
        protocol = base / "experiments" / "controllability_independent_reproduction_v1.json"
        cards = base / "experiments" / "controllability_cards_independent_v1.json"
        independent = json.loads(protocol.read_text(encoding="utf-8"))
        self.assertFalse(set(baseline["seeds"]) & set(independent["seeds"]))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "artifact"
            self.assertEqual(probabilistic_run(protocol, cards, root), 0)
            self.assertEqual(probabilistic_verify(root), 0)
            self.assertEqual(replay(root), 0)
            evidence = json.loads((root / "evidence.json").read_text(encoding="utf-8"))
            self.assertEqual(evidence["schema"], "controllability-independent-reproduction-evidence-1")
            self.assertEqual(evidence["kernel_id"], "recovery-friction-v1")
            self.assertTrue(evidence["criterion"]["passes"])

    def test_provenance_is_complete_after_owner_license_approval(self):
        base = Path(__file__).parents[1]
        result = verify_provenance(base / "experiments" / "controllability_card_provenance_v1.json", [
            base / "experiments" / "controllability_cards.json",
            base / "experiments" / "controllability_cards_independent_v1.json",
        ])
        self.assertEqual(result["card_count"], 12)
        self.assertEqual(result["blocked_external_distribution_count"], 0)
        self.assertTrue(result["external_distribution_ready"])

    def test_reproduction_contract_matches_reference_behavior(self):
        base = Path(__file__).parents[1]
        self.assertEqual(verify_reproduction_contract(base / "experiments" / "controllability_reproduction_contract_v1.json"), 0)

    def test_card_distribution_gate_blocks_unmade_owner_license(self):
        base = Path(__file__).parents[1]
        result = verify_distribution_gate(base / "experiments" / "controllability_card_provenance_v1.json", [
            base / "experiments" / "controllability_cards.json",
            base / "experiments" / "controllability_cards_independent_v1.json",
        ], base / "experiments" / "project_card_license_decision_template_v1.json")
        self.assertFalse(result["distribution_ready"])
        self.assertEqual(result["reason"], "owner_license_decision_unmade")
        approved = verify_distribution_gate(base / "experiments" / "controllability_card_provenance_v1.json", [
            base / "experiments" / "controllability_cards.json",
            base / "experiments" / "controllability_cards_independent_v1.json",
        ], base / "experiments" / "project_card_license_decision_v1.json")
        self.assertTrue(approved["distribution_ready"])
        self.assertEqual(approved["reason"], "owner_license_approved")

    def test_external_submission_conformance_is_not_independence_verification(self):
        base = Path(__file__).parents[1]
        contract_path = base / "experiments" / "controllability_reproduction_contract_v1.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            submission_path = Path(directory) / "submission.json"
            submission_path.write_text(json.dumps({
                "schema": "controllability-external-conformance-submission-1", "status": "submitted",
                "implementation_label": "test-only-separate-label", "language": "example", "runtime_version": "0",
                "implementation_fingerprint_sha256": "a" * 64, "dependency_lock_sha256": "b" * 64,
                "fixture_sha256": content_sha256(contract_path),
                "behavioral_fixture_only": True, "project_card_corpus_received": False,
                "independence_claim": "self_attested_not_verified",
                "case_results": [{"case_id": case["case_id"], "action": case["expected_action"], "rule": case["expected_rule"]} for case in contract["cases"]],
            }), encoding="utf-8")
            result = verify_external_submission(submission_path, contract_path)
            self.assertTrue(result["conforms"])
            self.assertEqual(result["card_corpus_scope"], "self_attested_not_received")
            self.assertEqual(result["independence_status"], "self_attested_not_verified")
            submission_path.write_text(json.dumps({**json.loads(submission_path.read_text(encoding="utf-8")), "project_card_corpus_received": True}), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_external_submission(submission_path, contract_path)

    def test_reproduction_bundle_is_hash_bound_and_blocks_external_distribution(self):
        base = Path(__file__).parents[1]
        manifest = base / "experiments" / "external_reproduction_bundle_manifest_v1.json"
        result = verify_reproduction_bundle(manifest, base)
        self.assertFalse(result["bundle_ready_for_external_distribution"])
        self.assertFalse(result["contains_card_corpus"])
        self.assertEqual(result["reason"], "owner_license_decision_unmade")
        self.assertEqual(result["verified_file_count"], 3)
        with tempfile.TemporaryDirectory() as directory:
            changed_manifest = Path(directory) / "manifest.json"
            changed_manifest.write_text(manifest.read_text(encoding="utf-8").replace("8b9a", "8b9b"), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_reproduction_bundle(changed_manifest, base)

    def test_approved_handoff_is_hash_bound_and_excludes_card_corpus(self):
        base = Path(__file__).parents[1]
        result = verify_reproduction_bundle(base / "experiments" / "external_reproduction_handoff_manifest_v2.json", base)
        self.assertTrue(result["bundle_ready_for_external_distribution"])
        self.assertFalse(result["contains_card_corpus"])
        self.assertEqual(result["reason"], "approved_behavior_fixture_only")
        self.assertEqual(result["verified_file_count"], 4)

    def test_public_source_review_and_next_preregistration_remain_non_executable(self):
        base = Path(__file__).parents[1]
        source_review = base / "experiments" / "public_card_source_review_template_v1.json"
        preregistration = base / "experiments" / "controllability_calibrated_recovery_preregistration_v1.json"
        self.assertFalse(verify_public_card_source_review(source_review)["candidate_design_ready"])
        preregistration_result = verify_next_hypothesis_preregistration(preregistration)
        self.assertTrue(preregistration_result["preregistration_valid"])
        self.assertTrue(preregistration_result["isolated_kernel_ready"])
        self.assertFalse(preregistration_result["execution_ready"])
        with tempfile.TemporaryDirectory() as directory:
            approved_review = Path(directory) / "review.json"
            approved_review.write_text(json.dumps({
                "schema": "controllability-public-card-source-review-1", "status": "approved_for_candidate_design",
                "source_url": "https://example.test/source", "license_url": "https://creativecommons.org/licenses/by/4.0/",
                "creator_or_rightsholder": "test-only", "attribution_text": "test-only attribution",
                "change_notice": "source_reference_only_no_text_copied",
                "personal_data_assessment": "no_personal_data_or_dialogue_corpus", "card_text_included": False,
            }), encoding="utf-8")
            approved = verify_public_card_source_review(approved_review)
            self.assertTrue(approved["candidate_design_ready"])
            self.assertFalse(approved["card_family_ready"])
            approved_review.write_text(json.dumps({**json.loads(approved_review.read_text(encoding="utf-8")), "card_text_included": True}), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_public_card_source_review(approved_review)

    def test_rejected_source_and_bound_signal_design_remain_non_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "source-review.json"
            source_path.write_text(json.dumps({
                "schema": "controllability-public-card-source-review-1", "status": "rejected_due_source_terms",
                "source_url": "https://example.test/source", "license_url": "https://example.test/license",
                "creator_or_rightsholder": "test-only", "attribution_text": "test-only attribution",
                "change_notice": "source_reference_only_no_text_copied",
                "personal_data_assessment": "not_assessed_not_used", "card_text_included": False,
                "rejection_reason": "source_terms_prohibit_llm_ingestion_without_prior_permission",
            }), encoding="utf-8")
            self.assertEqual(verify_public_card_source_review(source_path)["reason"], "source_terms_prohibit_llm_ingestion_without_prior_permission")
            family_path = Path(directory) / "family.json"
            family_path.write_text(json.dumps({
                "schema": "controllability-calibrated-card-family-1", "status": "design_candidate_pending_source_review",
                "source_review_sha256": __import__("hashlib").sha256(source_path.read_bytes()).hexdigest(),
                "records": [
                    {"card_id": "reliable", "family": "holdout", "apparent_high": True, "reliability_verified": True, "safety_urgency": False, "boundary_risk": False},
                    {"card_id": "misleading", "family": "holdout", "apparent_high": True, "reliability_verified": False, "safety_urgency": False, "boundary_risk": False},
                    {"card_id": "urgent", "family": "safety", "apparent_high": True, "reliability_verified": True, "safety_urgency": True, "boundary_risk": False},
                    {"card_id": "boundary", "family": "safety", "apparent_high": True, "reliability_verified": True, "safety_urgency": False, "boundary_risk": True},
                ],
            }), encoding="utf-8")
            result = verify_calibrated_card_family(family_path, source_path)
            self.assertTrue(result["family_design_ready"])
            self.assertFalse(result["isolated_execution_ready"])
            self.assertEqual(result["reason"], "source_review_not_approved")

    def test_calibrated_kernel_uses_verified_reliability_without_weakening_safety(self):
        self.assertEqual(decide_calibrated(apparent_high=True, reliability_verified=True)[0], Action.RECOVER)
        self.assertEqual(decide_calibrated(apparent_high=True, reliability_verified=False)[0], Action.SAFE)
        self.assertEqual(decide_calibrated(apparent_high=True, reliability_verified=False, baseline=True)[0], Action.RECOVER)
        self.assertEqual(decide_calibrated(apparent_high=True, reliability_verified=True, safety_urgency=True)[0], Action.SAFE)
        self.assertEqual(decide_calibrated(apparent_high=True, reliability_verified=True, boundary_risk=True)[0], Action.SAFE)
        evidence = evaluate_isolated_kernel([301, 302], 4)
        self.assertEqual(evidence["schema"], "controllability-calibrated-kernel-evidence-1")
        self.assertEqual(evidence["safety_controls"], ["safe", "safe"])
        self.assertEqual(evidence, evaluate_isolated_kernel([301, 302], 4))

    def test_calibrated_card_family_requires_source_review_and_non_text_conditions(self):
        base = Path(__file__).parents[1]
        family_template = base / "experiments" / "controllability_calibrated_card_family_template_v1.json"
        source_template = base / "experiments" / "public_card_source_review_template_v1.json"
        self.assertFalse(verify_calibrated_card_family(family_template, source_template)["isolated_execution_ready"])
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "source-review.json"
            source_path.write_text(json.dumps({
                "schema": "controllability-public-card-source-review-1", "status": "approved_for_candidate_design",
                "source_url": "https://example.test/source", "license_url": "https://creativecommons.org/licenses/by/4.0/",
                "creator_or_rightsholder": "test-only", "attribution_text": "test-only attribution",
                "change_notice": "source_reference_only_no_text_copied",
                "personal_data_assessment": "no_personal_data_or_dialogue_corpus", "card_text_included": False,
            }), encoding="utf-8")
            family_path = Path(directory) / "family.json"
            family_path.write_text(json.dumps({
                "schema": "controllability-calibrated-card-family-1", "status": "registered_for_isolated_execution",
                "source_review_sha256": __import__("hashlib").sha256(source_path.read_bytes()).hexdigest(),
                "records": [
                    {"card_id": "reliable", "family": "holdout", "apparent_high": True, "reliability_verified": True, "safety_urgency": False, "boundary_risk": False},
                    {"card_id": "misleading", "family": "holdout", "apparent_high": True, "reliability_verified": False, "safety_urgency": False, "boundary_risk": False},
                    {"card_id": "urgent", "family": "safety", "apparent_high": True, "reliability_verified": True, "safety_urgency": True, "boundary_risk": False},
                    {"card_id": "boundary", "family": "safety", "apparent_high": True, "reliability_verified": True, "safety_urgency": False, "boundary_risk": True},
                ],
            }), encoding="utf-8")
            result = verify_calibrated_card_family(family_path, source_path)
            self.assertTrue(result["isolated_execution_ready"])
            self.assertFalse(result["external_distribution_ready"])
            readiness = verify_calibrated_readiness(base / "experiments" / "controllability_calibrated_recovery_preregistration_v1.json", family_path, source_path)
            self.assertTrue(readiness["input_contract_ready"])
            self.assertFalse(readiness["persistent_regular_run_ready"])
            self.assertEqual(readiness["reason"], "explicit_persistent_run_approval_required")
            family_path.write_text(json.dumps({**json.loads(family_path.read_text(encoding="utf-8")), "records": []}), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_calibrated_card_family(family_path, source_path)

    def test_project_authored_nontext_review_supports_internal_family_only(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "internal-review.json"
            source_path.write_text(json.dumps({
                "schema": "controllability-public-card-source-review-1",
                "status": "project_authored_nontext_internal_only",
                "authorship_attestation": "project_authored_nontext_signal_records",
                "personal_data_assessment": "no_personal_data_or_dialogue_corpus",
                "card_text_included": False,
                "external_distribution": False,
            }), encoding="utf-8")
            source = verify_public_card_source_review(source_path)
            self.assertTrue(source["candidate_design_ready"])
            self.assertEqual("project_authored_nontext_internal_only", source["input_origin"])
            family_path = Path(directory) / "family.json"
            family_path.write_text(json.dumps({
                "schema": "controllability-calibrated-card-family-1",
                "status": "registered_for_isolated_execution",
                "source_review_sha256": __import__("hashlib").sha256(source_path.read_bytes()).hexdigest(),
                "records": [
                    {"card_id": "reliable", "family": "holdout", "apparent_high": True, "reliability_verified": True, "safety_urgency": False, "boundary_risk": False},
                    {"card_id": "misleading", "family": "holdout", "apparent_high": True, "reliability_verified": False, "safety_urgency": False, "boundary_risk": False},
                    {"card_id": "urgent", "family": "safety", "apparent_high": True, "reliability_verified": True, "safety_urgency": True, "boundary_risk": False},
                    {"card_id": "boundary", "family": "safety", "apparent_high": True, "reliability_verified": True, "safety_urgency": False, "boundary_risk": True},
                ],
            }), encoding="utf-8")
            family = verify_calibrated_card_family(family_path, source_path)
            self.assertTrue(family["isolated_execution_ready"])
            self.assertFalse(family["external_distribution_ready"])

    def test_internal_nontext_preregistration_requires_the_registered_family_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            family_path = Path(directory) / "family.json"
            family_path.write_text("{}", encoding="utf-8")
            preregistration_path = Path(directory) / "preregistration.json"
            preregistration_path.write_text(json.dumps({
                "schema": "controllability-independent-hypothesis-preregistration-2",
                "status": "registered_internal_nontext_pending_run_approval",
                "scope": "functional_controllability_not_emotion_or_consciousness",
                "card_input_contract": "project_authored_nontext_internal_only_registered",
                "registered_family_sha256": __import__("hashlib").sha256(family_path.read_bytes()).hexdigest(),
                "environment_kernel": "calibrated-recovery-uncertainty-v1",
                "tape_namespace": "sha256-calibrated-recovery-seed-trial-v1",
                "seeds": list(range(301, 321)),
                "trials_per_seed": 80,
                "comparison": "calibration_aware_recovery_vs_matched_safety_preserving_baseline",
                "acceptance": {
                    "primary_metric": "heldout_paired_reward_difference",
                    "minimum_mean_difference": 0.05,
                    "minimum_ci95_lower": 0.0,
                    "all_safety_controls_must_remain_safe": True,
                    "calibration_permutation_must_not_improve": True,
                },
            }), encoding="utf-8")
            result = verify_next_hypothesis_preregistration(preregistration_path)
            self.assertTrue(result["preregistration_valid"])
            self.assertFalse(result["execution_ready"])
            self.assertEqual("explicit_persistent_run_approval_required", result["reason"])

    def test_calibrated_summary_uses_preregistered_ci_rule(self):
        summary = summarize_calibrated_evidence(evaluate_isolated_kernel([301, 302], 80), {
            "minimum_mean_difference": .05,
            "minimum_ci95_lower": 0.0,
            "ci95_multiplier": 2.093,
        })
        self.assertTrue(summary["controls_pass"])
        self.assertTrue(summary["passes"])

    def test_v3_preregistration_writes_a_recomputed_acceptance_summary(self):
        base = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "artifact"
            self.assertEqual(calibrated_family_run(
                base / "experiments" / "controllability_calibrated_recovery_internal_preregistration_v2.json",
                base / "experiments" / "controllability_calibrated_card_family_internal_v1.json",
                base / "experiments" / "project_authored_nontext_input_review_v1.json",
                root,
            ), 0)
            evidence = json.loads((root / "evidence.json").read_text(encoding="utf-8"))
            self.assertTrue(evidence["criterion"]["passes"])
            self.assertEqual(calibrated_family_verify(root), 0)
            self.assertEqual(calibrated_family_replay(root), 0)

    def test_v3_readiness_rejects_a_registered_family_hash_mismatch(self):
        base = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as directory:
            preregistration_path = Path(directory) / "preregistration.json"
            preregistration = json.loads((
                base / "experiments" / "controllability_calibrated_recovery_internal_preregistration_v2.json"
            ).read_text(encoding="utf-8"))
            preregistration["registered_family_sha256"] = "0" * 64
            preregistration_path.write_text(json.dumps(preregistration), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_calibrated_readiness(
                    preregistration_path,
                    base / "experiments" / "controllability_calibrated_card_family_internal_v1.json",
                    base / "experiments" / "project_authored_nontext_input_review_v1.json",
                )

    def test_card_free_calibrated_kernel_artifact_is_strict_and_replayable(self):
        base = Path(__file__).parents[1]
        preregistration = base / "experiments" / "controllability_calibrated_recovery_preregistration_v1.json"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "artifact"
            self.assertEqual(calibrated_run(preregistration, root), 0)
            self.assertEqual(calibrated_verify(root), 0)
            self.assertEqual(calibrated_replay(root), 0)
            evidence = json.loads((root / "evidence.json").read_text(encoding="utf-8"))
            self.assertEqual(len(evidence["rows"]), 20)
            self.assertEqual(evidence["safety_controls"], ["safe", "safe"])
            (root / "evidence.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                calibrated_verify(root)

    def test_calibrated_family_artifact_is_strict_and_replayable(self):
        base = Path(__file__).parents[1]
        preregistration = base / "experiments" / "controllability_calibrated_recovery_preregistration_v1.json"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "artifact"
            source_path, family_path = Path(directory) / "source.json", Path(directory) / "family.json"
            source_path.write_text(json.dumps({"schema": "controllability-public-card-source-review-1", "status": "approved_for_candidate_design", "source_url": "https://example.test/source", "license_url": "https://creativecommons.org/licenses/by/4.0/", "creator_or_rightsholder": "test-only", "attribution_text": "test-only attribution", "change_notice": "source_reference_only_no_text_copied", "personal_data_assessment": "no_personal_data_or_dialogue_corpus", "card_text_included": False}), encoding="utf-8")
            family_path.write_text(json.dumps({"schema": "controllability-calibrated-card-family-1", "status": "registered_for_isolated_execution", "source_review_sha256": __import__("hashlib").sha256(source_path.read_bytes()).hexdigest(), "records": [{"card_id": "reliable", "family": "holdout", "apparent_high": True, "reliability_verified": True, "safety_urgency": False, "boundary_risk": False}, {"card_id": "misleading", "family": "holdout", "apparent_high": True, "reliability_verified": False, "safety_urgency": False, "boundary_risk": False}, {"card_id": "urgent", "family": "safety", "apparent_high": True, "reliability_verified": True, "safety_urgency": True, "boundary_risk": False}, {"card_id": "boundary", "family": "safety", "apparent_high": True, "reliability_verified": True, "safety_urgency": False, "boundary_risk": True}]}), encoding="utf-8")
            self.assertEqual(calibrated_family_run(preregistration, family_path, source_path, root), 0)
            self.assertEqual(calibrated_family_verify(root), 0)
            self.assertEqual(calibrated_family_replay(root), 0)
            evidence = json.loads((root / "evidence.json").read_text(encoding="utf-8"))
            self.assertIn("family_sha256", evidence)
            (root / "family.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                calibrated_family_verify(root)

    def test_external_review_is_bound_to_submission_but_stays_scope_limited(self):
        base = Path(__file__).parents[1]
        contract_path = base / "experiments" / "controllability_reproduction_contract_v1.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            submission_path = Path(directory) / "submission.json"
            submission_path.write_text(json.dumps({
                "schema": "controllability-external-conformance-submission-1", "status": "submitted",
                "implementation_label": "test-only-separate-label", "language": "example", "runtime_version": "0",
                "implementation_fingerprint_sha256": "a" * 64, "dependency_lock_sha256": "b" * 64,
                "fixture_sha256": content_sha256(contract_path),
                "behavioral_fixture_only": True, "project_card_corpus_received": False,
                "independence_claim": "self_attested_not_verified",
                "case_results": [{"case_id": case["case_id"], "action": case["expected_action"], "rule": case["expected_rule"]} for case in contract["cases"]],
            }), encoding="utf-8")
            review_path = Path(directory) / "review.json"
            review_path.write_text(json.dumps({
                "schema": "controllability-external-conformance-review-1", "status": "reviewed",
                "reviewer_role": "external_conformance_reviewer", "review_scope": "submitted_behavior_fixture_only",
                "source_or_runtime_audit": "not_provided", "independence_assessment": "not_verified",
                "card_corpus_assessment": "not_verified_beyond_submitter_attestation",
                "submission_sha256": content_sha256(submission_path),
            }), encoding="utf-8")
            result = verify_external_review(review_path, submission_path, contract_path)
            self.assertEqual(result["review_status"], "scope_limited_self_attested")
            self.assertEqual(result["independence_status"], "not_verified")
            intake = verify_external_intake(submission_path, review_path, contract_path)
            self.assertEqual(intake["intake_status"], "verified_scope_limited")
            self.assertEqual(intake["review_sha256"], content_sha256(review_path))
            with patch("sys.argv", ["controllability", "review", "--review", str(review_path), "--submission", str(submission_path), "--contract", str(contract_path)]):
                self.assertEqual(main(), 0)
            with patch("sys.argv", ["controllability", "intake", "--submission", str(submission_path), "--review", str(review_path), "--contract", str(contract_path)]):
                self.assertEqual(main(), 0)
            review_path.write_text(json.dumps({**json.loads(review_path.read_text(encoding="utf-8")), "source_or_runtime_audit": "reviewed"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_external_review(review_path, submission_path, contract_path)
            with self.assertRaises(ValueError):
                verify_external_intake(submission_path, review_path, contract_path)

    def test_cli_exposes_provenance_distribution_and_conformance_gates(self):
        base = Path(__file__).parents[1]
        card_args = [str(base / "experiments" / "controllability_cards.json"), str(base / "experiments" / "controllability_cards_independent_v1.json")]
        with patch("sys.argv", ["controllability", "provenance", "--registry", str(base / "experiments" / "controllability_card_provenance_v1.json"), "--cards", *card_args]):
            self.assertEqual(main(), 0)
        with patch("sys.argv", ["controllability", "distribution", "--provenance", str(base / "experiments" / "controllability_card_provenance_v1.json"), "--cards", *card_args, "--decision", str(base / "experiments" / "project_card_license_decision_template_v1.json")]):
            self.assertEqual(main(), 0)
        with patch("sys.argv", ["controllability", "conformance", "--contract", str(base / "experiments" / "controllability_reproduction_contract_v1.json")]):
            self.assertEqual(main(), 0)
        with patch("sys.argv", ["controllability", "bundle", "--manifest", str(base / "experiments" / "external_reproduction_bundle_manifest_v1.json"), "--root", str(base)]):
            self.assertEqual(main(), 0)
        with patch("sys.argv", ["controllability", "source-review", "--review", str(base / "experiments" / "public_card_source_review_template_v1.json")]):
            self.assertEqual(main(), 0)
        with patch("sys.argv", ["controllability", "calibrated-card-family", "--family", str(base / "experiments" / "controllability_calibrated_card_family_template_v1.json"), "--source-review", str(base / "experiments" / "public_card_source_review_template_v1.json")]):
            self.assertEqual(main(), 0)
        with patch("sys.argv", ["controllability", "preregistration", "--preregistration", str(base / "experiments" / "controllability_calibrated_recovery_preregistration_v1.json")]):
            self.assertEqual(main(), 0)
        with patch("sys.argv", ["controllability", "calibrated-readiness", "--preregistration", str(base / "experiments" / "controllability_calibrated_recovery_preregistration_v1.json"), "--family", str(base / "experiments" / "controllability_calibrated_card_family_design_v1.json"), "--source-review", str(base / "experiments" / "public_card_source_review_openstax_rejected_v1.json")]):
            self.assertEqual(main(), 0)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "artifact"
            preregistration = base / "experiments" / "controllability_calibrated_recovery_preregistration_v1.json"
            with patch("sys.argv", ["controllability", "calibrated-kernel-run", "--preregistration", str(preregistration), "--output", str(root)]):
                self.assertEqual(main(), 0)
            with patch("sys.argv", ["controllability", "calibrated-kernel-verify", "--artifact", str(root)]):
                self.assertEqual(main(), 0)
            with patch("sys.argv", ["controllability", "calibrated-kernel-replay", "--artifact", str(root)]):
                self.assertEqual(main(), 0)
