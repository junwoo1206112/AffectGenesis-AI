"""Fail-closed provenance and cross-implementation conformance checks."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

from .core import Card, decide
from .evidence import load_cards


_REPRODUCTION_BUNDLE_FILES = {
    "experiments/controllability_reproduction_contract_v1.json",
    "experiments/external_conformance_submission_template_v1.json",
    "experiments/project_card_license_decision_template_v1.json",
}

_APPROVED_REPRODUCTION_HANDOFF_FILES = {
    "experiments/controllability_reproduction_contract_v1.json",
    "experiments/external_conformance_submission_template_v1.json",
    "experiments/project_card_license_decision_v1.json",
    "docs/카드_CC_BY_4_0_라이선스.md",
}


def _content_sha256(path: Path) -> str:
    """Hash repository text content independent of Windows checkout line endings."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def verify_public_card_source_review(path: Path) -> dict[str, object]:
    """Validate reviewed public sources or project-authored non-text inputs."""
    review = json.loads(path.read_text(encoding="utf-8"))
    if type(review) is not dict or review.get("schema") != "controllability-public-card-source-review-1":
        raise ValueError("invalid public card source review")
    if review.get("status") == "project_authored_nontext_internal_only":
        required = {
            "schema", "status", "authorship_attestation", "personal_data_assessment",
            "card_text_included", "external_distribution",
        }
        if (
            set(review) != required
            or review.get("authorship_attestation") != "project_authored_nontext_signal_records"
            or review.get("personal_data_assessment") != "no_personal_data_or_dialogue_corpus"
            or review.get("card_text_included") is not False
            or review.get("external_distribution") is not False
        ):
            raise ValueError("invalid project-authored non-text input review")
        return {
            "candidate_design_ready": True,
            "card_family_ready": False,
            "input_origin": "project_authored_nontext_internal_only",
            "reason": "card_family_not_yet_registered_or_distributable",
        }
    if review.get("status") == "rejected_due_source_terms":
        required_text = ("source_url", "license_url", "creator_or_rightsholder", "attribution_text")
        if (any(type(review.get(field)) is not str or not review[field] for field in required_text)
                or not review["source_url"].startswith("https://")
                or not review["license_url"].startswith("https://")
                or review.get("change_notice") != "source_reference_only_no_text_copied"
                or review.get("personal_data_assessment") != "not_assessed_not_used"
                or review.get("card_text_included") is not False
                or review.get("rejection_reason") != "source_terms_prohibit_llm_ingestion_without_prior_permission"):
            raise ValueError("invalid rejected public card source review")
        return {"candidate_design_ready": False, "card_family_ready": False,
                "reason": "source_terms_prohibit_llm_ingestion_without_prior_permission"}
    if review.get("status") != "approved_for_candidate_design":
        return {"candidate_design_ready": False, "card_family_ready": False,
                "reason": "source_license_review_unmade"}
    required_text = ("source_url", "license_url", "creator_or_rightsholder", "attribution_text")
    if (any(type(review.get(field)) is not str or not review[field] for field in required_text)
            or not review["source_url"].startswith("https://")
            or not review["license_url"].startswith("https://")
            or review.get("change_notice") != "source_reference_only_no_text_copied"
            or review.get("personal_data_assessment") != "no_personal_data_or_dialogue_corpus"
            or review.get("card_text_included") is not False):
        raise ValueError("invalid approved public card source review")
    return {"candidate_design_ready": True, "card_family_ready": False,
            "input_origin": "public_source", "reason": "card_family_not_yet_registered_or_distributable"}


def verify_calibrated_card_family(path: Path, source_review_path: Path) -> dict[str, object]:
    """Validate only non-text synthetic signal records after source review."""
    family = json.loads(path.read_text(encoding="utf-8"))
    if type(family) is not dict or family.get("schema") != "controllability-calibrated-card-family-1":
        raise ValueError("invalid calibrated card family")
    status = family.get("status")
    if status not in {"registered_for_isolated_execution", "design_candidate_pending_source_review"}:
        return {"isolated_execution_ready": False, "external_distribution_ready": False,
                "reason": "calibrated_card_family_not_registered"}
    source = verify_public_card_source_review(source_review_path)
    if family.get("source_review_sha256") != _content_sha256(source_review_path):
        raise ValueError("calibrated card family source review mismatch")
    records = family.get("records")
    required = {"card_id", "family", "apparent_high", "reliability_verified", "safety_urgency", "boundary_risk"}
    if type(records) is not list or len(records) != 4 or len({record.get("card_id") for record in records if type(record) is dict}) != 4:
        raise ValueError("invalid calibrated card records")
    for record in records:
        if (type(record) is not dict or set(record) != required
                or type(record["card_id"]) is not str or not record["card_id"]
                or record["family"] not in {"holdout", "safety"}
                or any(type(record[field]) is not bool for field in required - {"card_id", "family"})):
            raise ValueError("invalid calibrated card record")
    signatures = {(record["family"], record["apparent_high"], record["reliability_verified"], record["safety_urgency"], record["boundary_risk"]) for record in records}
    expected = {("holdout", True, True, False, False), ("holdout", True, False, False, False),
                ("safety", True, True, True, False), ("safety", True, True, False, True)}
    if signatures != expected:
        raise ValueError("incomplete calibrated card conditions")
    if status == "design_candidate_pending_source_review":
        return {"family_design_ready": True, "isolated_execution_ready": False,
                "external_distribution_ready": False, "reason": "source_review_not_approved"}
    if not source["candidate_design_ready"]:
        return {"isolated_execution_ready": False, "external_distribution_ready": False,
                "reason": "source_review_not_ready"}
    return {"isolated_execution_ready": True, "external_distribution_ready": False,
            "card_count": len(records), "reason": "owner_distribution_decision_pending"}


def verify_next_hypothesis_preregistration(path: Path) -> dict[str, object]:
    """Validate a design-only, non-executable next hypothesis without tuning prior results."""
    preregistration = json.loads(path.read_text(encoding="utf-8"))
    is_public_design = (
        type(preregistration) is dict
        and preregistration.get("schema") == "controllability-independent-hypothesis-preregistration-1"
        and preregistration.get("status") == "design_only_pending_source_review"
        and preregistration.get("card_input_contract") == "publicly_reviewed_synthetic_candidates_not_yet_registered"
    )
    is_internal_registration = (
        type(preregistration) is dict
        and preregistration.get("schema") == "controllability-independent-hypothesis-preregistration-2"
        and preregistration.get("status") == "registered_internal_nontext_pending_run_approval"
        and preregistration.get("card_input_contract") == "project_authored_nontext_internal_only_registered"
        and type(preregistration.get("registered_family_sha256")) is str
        and len(preregistration["registered_family_sha256"]) == 64
    )
    is_internal_registration_v3 = (
        type(preregistration) is dict
        and preregistration.get("schema") == "controllability-independent-hypothesis-preregistration-3"
        and preregistration.get("status") == "registered_internal_nontext_pending_run_approval"
        and preregistration.get("card_input_contract") == "project_authored_nontext_internal_only_registered"
        and type(preregistration.get("registered_family_sha256")) is str
        and len(preregistration["registered_family_sha256"]) == 64
    )
    if (not (is_public_design or is_internal_registration or is_internal_registration_v3)
            or preregistration.get("scope") != "functional_controllability_not_emotion_or_consciousness"
            or preregistration.get("environment_kernel") != "calibrated-recovery-uncertainty-v1"
            or preregistration.get("tape_namespace") != "sha256-calibrated-recovery-seed-trial-v1"):
        raise ValueError("invalid next hypothesis preregistration")
    seeds = preregistration.get("seeds")
    acceptance = preregistration.get("acceptance")
    if (seeds != list(range(301, 321)) or preregistration.get("trials_per_seed") != 80
            or type(acceptance) is not dict
            or acceptance.get("primary_metric") != "heldout_paired_reward_difference"
            or acceptance.get("minimum_mean_difference") != 0.05
            or acceptance.get("minimum_ci95_lower") != 0.0
            or acceptance.get("all_safety_controls_must_remain_safe") is not True
            or acceptance.get("calibration_permutation_must_not_improve") is not True
            or (is_internal_registration_v3 and acceptance.get("ci95_multiplier") != 2.093)
            or (not is_internal_registration_v3 and "ci95_multiplier" in acceptance)):
        raise ValueError("invalid next hypothesis acceptance")
    return {
        "preregistration_valid": True,
        "isolated_kernel_ready": True,
        "execution_ready": False,
        "reason": (
            "explicit_persistent_run_approval_required"
            if (is_internal_registration or is_internal_registration_v3)
            else "public_source_review_and_card_family_implementation_pending"
        ),
    }


def verify_calibrated_readiness(preregistration_path: Path, family_path: Path, source_review_path: Path) -> dict[str, object]:
    """Report each input gate without creating an artifact or granting run authority."""
    source = verify_public_card_source_review(source_review_path)
    family = verify_calibrated_card_family(family_path, source_review_path)
    preregistration = verify_next_hypothesis_preregistration(preregistration_path)
    preregistration_record = json.loads(preregistration_path.read_text(encoding="utf-8"))
    if (
        preregistration_record.get("schema") in {
            "controllability-independent-hypothesis-preregistration-2",
            "controllability-independent-hypothesis-preregistration-3",
        }
        and preregistration_record["registered_family_sha256"] != _content_sha256(family_path)
    ):
        raise ValueError("internal preregistration family mismatch")
    if not source["candidate_design_ready"]:
        reason = "source_review_not_approved"
    elif not family["isolated_execution_ready"]:
        reason = "family_not_registered_for_isolated_execution"
    else:
        reason = "explicit_persistent_run_approval_required"
    return {
        "schema": "controllability-calibrated-readiness-1",
        "source_review": source,
        "family": family,
        "preregistration": preregistration,
        "input_contract_ready": source["candidate_design_ready"] and family["isolated_execution_ready"] and preregistration["preregistration_valid"],
        "persistent_regular_run_ready": False,
        "reason": reason,
    }


def verify_reproduction_bundle(manifest_path: Path, root: Path) -> dict[str, object]:
    """Verify a no-card-corpus reproduction preflight without exporting it."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if type(manifest) is not dict or manifest.get("scope") != "behavioral_conformance_only_no_card_corpus":
        raise ValueError("invalid reproduction bundle manifest")
    is_approved_handoff = manifest.get("schema") == "controllability-external-reproduction-bundle-2"
    if manifest.get("schema") not in {
        "controllability-external-reproduction-bundle-1",
        "controllability-external-reproduction-bundle-2",
    } or manifest.get("external_distribution") != (
        "approved_behavior_fixture_only" if is_approved_handoff else "blocked_pending_owner_license"
    ):
        raise ValueError("invalid reproduction bundle manifest")
    expected_files = _APPROVED_REPRODUCTION_HANDOFF_FILES if is_approved_handoff else _REPRODUCTION_BUNDLE_FILES
    files = manifest.get("files")
    if type(files) is not list or len(files) != len(expected_files):
        raise ValueError("invalid reproduction bundle files")
    by_path: dict[str, str] = {}
    for entry in files:
        if (type(entry) is not dict or type(entry.get("path")) is not str
                or type(entry.get("sha256")) is not str or len(entry["sha256"]) != 64
                or entry["path"] in by_path):
            raise ValueError("invalid reproduction bundle file")
        by_path[entry["path"]] = entry["sha256"]
    if set(by_path) != expected_files:
        raise ValueError("unexpected reproduction bundle file")
    root = root.resolve()
    for relative_path, expected_hash in by_path.items():
        file_path = (root / relative_path).resolve()
        if root not in file_path.parents or _content_sha256(file_path) != expected_hash:
            raise ValueError("reproduction bundle hash mismatch")
    verify_reproduction_contract(root / "experiments/controllability_reproduction_contract_v1.json")
    submission_template = json.loads((root / "experiments/external_conformance_submission_template_v1.json").read_text(encoding="utf-8"))
    decision_path = root / ("experiments/project_card_license_decision_v1.json" if is_approved_handoff else "experiments/project_card_license_decision_template_v1.json")
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    if (type(submission_template) is not dict
            or submission_template.get("schema") != "controllability-external-conformance-submission-1"
            or submission_template.get("status") != "template_not_submission"
            or type(decision) is not dict
            or decision.get("schema") != "project-card-license-decision-1"
            or decision.get("status") != ("approved" if is_approved_handoff else "unmade")):
        raise ValueError("invalid reproduction bundle boundary")
    if is_approved_handoff:
        distribution = verify_distribution_gate(
            root / "experiments/controllability_card_provenance_v1.json",
            [root / "experiments/controllability_cards.json", root / "experiments/controllability_cards_independent_v1.json"],
            decision_path,
        )
        if not distribution["distribution_ready"]:
            raise ValueError("approved reproduction handoff lacks distribution approval")
    return {"bundle_ready_for_external_distribution": is_approved_handoff,
            "contains_card_corpus": False,
            "reason": "approved_behavior_fixture_only" if is_approved_handoff else "owner_license_decision_unmade",
            "verified_file_count": len(by_path)}


def verify_provenance(path: Path, card_paths: list[Path]) -> dict[str, object]:
    registry = json.loads(path.read_text(encoding="utf-8"))
    if type(registry) is not dict or registry.get("schema") != "controllability-card-provenance-1":
        raise ValueError("invalid provenance registry")
    sources, records = registry.get("sources"), registry.get("cards")
    if type(sources) is not list or type(records) is not dict:
        raise ValueError("invalid provenance registry")
    source_ids = set()
    for source in sources:
        if type(source) is not dict or type(source.get("source_id")) is not str or source["source_id"] in source_ids:
            raise ValueError("invalid provenance source")
        source_ids.add(source["source_id"])
    card_ids = {card.card_id for card_path in card_paths for card in load_cards(card_path)}
    if set(records) != card_ids:
        raise ValueError("provenance card coverage mismatch")
    blocked = 0
    for card_id in card_ids:
        record = records[card_id]
        if type(record) is not dict or record.get("source_id") not in source_ids:
            raise ValueError("invalid provenance card")
        if record.get("external_distribution") == "blocked_pending_owner_license":
            blocked += 1
    return {"schema": registry["schema"], "card_count": len(card_ids), "blocked_external_distribution_count": blocked,
            "external_distribution_ready": blocked == 0}


def verify_reproduction_contract(path: Path) -> int:
    contract = json.loads(path.read_text(encoding="utf-8"))
    if type(contract) is not dict or contract.get("schema") != "controllability-reproduction-contract-1" or contract.get("scope") != "behavioral_conformance_only":
        raise ValueError("invalid reproduction contract")
    cases = contract.get("cases")
    if type(cases) is not list or len(cases) < 6 or len({case.get("case_id") for case in cases if type(case) is dict}) != len(cases):
        raise ValueError("invalid reproduction cases")
    for case in cases:
        if type(case) is not dict:
            raise ValueError("invalid reproduction case")
        card = Card(case["case_id"], "holdout", case["controllability"], case["recoverable"], case["safety_urgency"], case["boundary_risk"])
        action, rule = decide(card, ablated=case["ablated"], permute_label=case["permuted"])
        if action.value != case.get("expected_action") or rule != case.get("expected_rule"):
            raise ValueError("reproduction conformance mismatch")
    return 0


def verify_distribution_gate(provenance_path: Path, card_paths: list[Path], decision_path: Path) -> dict[str, object]:
    provenance = verify_provenance(provenance_path, card_paths)
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    if type(decision) is not dict or decision.get("schema") != "project-card-license-decision-1":
        raise ValueError("invalid license decision")
    if decision.get("status") != "approved":
        return {"distribution_ready": False, "reason": "owner_license_decision_unmade", "card_count": provenance["card_count"]}
    card_ids = {card.card_id for card_path in card_paths for card in load_cards(card_path)}
    if (type(decision.get("license_url")) is not str or not decision["license_url"]
            or decision.get("distribution_scope") != "all_registered_cards" or set(decision.get("approved_card_ids", [])) != card_ids):
        raise ValueError("invalid approved license decision")
    return {"distribution_ready": True, "reason": "owner_license_approved", "card_count": provenance["card_count"]}


def verify_external_submission(submission_path: Path, contract_path: Path) -> dict[str, object]:
    submission = json.loads(submission_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if (type(submission) is not dict or submission.get("schema") != "controllability-external-conformance-submission-1"
            or submission.get("status") != "submitted" or type(contract) is not dict):
        raise ValueError("invalid conformance submission")
    fingerprint_fields = ("implementation_fingerprint_sha256", "dependency_lock_sha256", "fixture_sha256")
    if (type(submission.get("implementation_label")) is not str or not submission["implementation_label"]
            or type(submission.get("language")) is not str or not submission["language"]
            or type(submission.get("runtime_version")) is not str or not submission["runtime_version"]
            or submission.get("independence_claim") != "self_attested_not_verified"
            or submission.get("behavioral_fixture_only") is not True
            or submission.get("project_card_corpus_received") is not False
            or any(type(submission.get(field)) is not str or len(submission[field]) != 64 for field in fingerprint_fields)):
        raise ValueError("invalid conformance submission metadata")
    if submission["fixture_sha256"] != _content_sha256(contract_path):
        raise ValueError("fixture hash mismatch")
    expected = {case["case_id"]: (case["expected_action"], case["expected_rule"]) for case in contract["cases"]}
    results = submission.get("case_results")
    if type(results) is not list or len(results) != len(expected):
        raise ValueError("invalid conformance case results")
    actual = {result.get("case_id"): (result.get("action"), result.get("rule")) for result in results if type(result) is dict}
    if actual != expected:
        raise ValueError("conformance results mismatch")
    return {"conforms": True, "card_corpus_scope": "self_attested_not_received",
            "independence_status": "self_attested_not_verified", "case_count": len(expected)}


def verify_external_review(review_path: Path, submission_path: Path, contract_path: Path) -> dict[str, object]:
    """Bind a limited review record to a valid submitted conformance result."""
    submission = verify_external_submission(submission_path, contract_path)
    review = json.loads(review_path.read_text(encoding="utf-8"))
    if (type(review) is not dict
            or review.get("schema") != "controllability-external-conformance-review-1"
            or review.get("status") != "reviewed"
            or review.get("reviewer_role") != "external_conformance_reviewer"
            or review.get("review_scope") != "submitted_behavior_fixture_only"
            or review.get("source_or_runtime_audit") != "not_provided"
            or review.get("independence_assessment") != "not_verified"
            or review.get("card_corpus_assessment") != "not_verified_beyond_submitter_attestation"
            or review.get("submission_sha256") != _content_sha256(submission_path)):
        raise ValueError("invalid conformance review")
    return {"conforms": submission["conforms"], "review_status": "scope_limited_self_attested",
            "independence_status": "not_verified", "source_or_runtime_audit": "not_provided"}


def verify_external_intake(submission_path: Path, review_path: Path, contract_path: Path) -> dict[str, object]:
    """Read-only combined verification for a received submission and review record."""
    review = verify_external_review(review_path, submission_path, contract_path)
    return {"intake_status": "verified_scope_limited",
            "submission_sha256": _content_sha256(submission_path),
            "review_sha256": _content_sha256(review_path),
            "contract_sha256": _content_sha256(contract_path),
            **review}
