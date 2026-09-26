"""CLI for the isolated probabilistic controllability protocol."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .probabilistic import replay, run, verify
from .calibrated_artifact import replay as calibrated_replay, run as calibrated_run, verify as calibrated_verify
from .calibrated_family_artifact import replay as calibrated_family_replay, run as calibrated_family_run, verify as calibrated_family_verify
from .provenance import verify_calibrated_card_family, verify_calibrated_readiness, verify_distribution_gate, verify_external_intake, verify_external_review, verify_external_submission, verify_next_hypothesis_preregistration, verify_provenance, verify_public_card_source_review, verify_reproduction_bundle, verify_reproduction_contract


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--protocol", type=Path, required=True)
    run_parser.add_argument("--cards", type=Path, required=True)
    run_parser.add_argument("--output", type=Path, required=True)
    for command in ("verify", "replay"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--artifact", type=Path, required=True)
    provenance_parser = subparsers.add_parser("provenance")
    provenance_parser.add_argument("--registry", type=Path, required=True)
    provenance_parser.add_argument("--cards", type=Path, nargs="+", required=True)
    distribution_parser = subparsers.add_parser("distribution")
    distribution_parser.add_argument("--provenance", type=Path, required=True)
    distribution_parser.add_argument("--cards", type=Path, nargs="+", required=True)
    distribution_parser.add_argument("--decision", type=Path, required=True)
    conformance_parser = subparsers.add_parser("conformance")
    conformance_parser.add_argument("--contract", type=Path, required=True)
    submission_parser = subparsers.add_parser("submission")
    submission_parser.add_argument("--submission", type=Path, required=True)
    submission_parser.add_argument("--contract", type=Path, required=True)
    bundle_parser = subparsers.add_parser("bundle")
    bundle_parser.add_argument("--manifest", type=Path, required=True)
    bundle_parser.add_argument("--root", type=Path, required=True)
    review_parser = subparsers.add_parser("review")
    review_parser.add_argument("--review", type=Path, required=True)
    review_parser.add_argument("--submission", type=Path, required=True)
    review_parser.add_argument("--contract", type=Path, required=True)
    intake_parser = subparsers.add_parser("intake")
    intake_parser.add_argument("--submission", type=Path, required=True)
    intake_parser.add_argument("--review", type=Path, required=True)
    intake_parser.add_argument("--contract", type=Path, required=True)
    source_review_parser = subparsers.add_parser("source-review")
    source_review_parser.add_argument("--review", type=Path, required=True)
    card_family_parser = subparsers.add_parser("calibrated-card-family")
    card_family_parser.add_argument("--family", type=Path, required=True)
    card_family_parser.add_argument("--source-review", type=Path, required=True)
    preregistration_parser = subparsers.add_parser("preregistration")
    preregistration_parser.add_argument("--preregistration", type=Path, required=True)
    readiness_parser = subparsers.add_parser("calibrated-readiness")
    readiness_parser.add_argument("--preregistration", type=Path, required=True)
    readiness_parser.add_argument("--family", type=Path, required=True)
    readiness_parser.add_argument("--source-review", type=Path, required=True)
    calibrated_run_parser = subparsers.add_parser("calibrated-kernel-run")
    calibrated_run_parser.add_argument("--preregistration", type=Path, required=True)
    calibrated_run_parser.add_argument("--output", type=Path, required=True)
    for command in ("calibrated-kernel-verify", "calibrated-kernel-replay"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--artifact", type=Path, required=True)
    calibrated_family_run_parser = subparsers.add_parser("calibrated-family-run")
    calibrated_family_run_parser.add_argument("--preregistration", type=Path, required=True)
    calibrated_family_run_parser.add_argument("--family", type=Path, required=True)
    calibrated_family_run_parser.add_argument("--source-review", type=Path, required=True)
    calibrated_family_run_parser.add_argument("--output", type=Path, required=True)
    for command in ("calibrated-family-verify", "calibrated-family-replay"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--artifact", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.command == "run":
        return run(arguments.protocol, arguments.cards, arguments.output)
    if arguments.command == "verify":
        return verify(arguments.artifact)
    if arguments.command == "replay":
        return replay(arguments.artifact)
    if arguments.command == "provenance":
        print(json.dumps(verify_provenance(arguments.registry, arguments.cards), sort_keys=True))
        return 0
    if arguments.command == "distribution":
        print(json.dumps(verify_distribution_gate(arguments.provenance, arguments.cards, arguments.decision), sort_keys=True))
        return 0
    if arguments.command == "conformance":
        return verify_reproduction_contract(arguments.contract)
    if arguments.command == "bundle":
        print(json.dumps(verify_reproduction_bundle(arguments.manifest, arguments.root), sort_keys=True))
        return 0
    if arguments.command == "review":
        print(json.dumps(verify_external_review(arguments.review, arguments.submission, arguments.contract), sort_keys=True))
        return 0
    if arguments.command == "intake":
        print(json.dumps(verify_external_intake(arguments.submission, arguments.review, arguments.contract), sort_keys=True))
        return 0
    if arguments.command == "source-review":
        print(json.dumps(verify_public_card_source_review(arguments.review), sort_keys=True))
        return 0
    if arguments.command == "calibrated-card-family":
        print(json.dumps(verify_calibrated_card_family(arguments.family, arguments.source_review), sort_keys=True))
        return 0
    if arguments.command == "preregistration":
        print(json.dumps(verify_next_hypothesis_preregistration(arguments.preregistration), sort_keys=True))
        return 0
    if arguments.command == "calibrated-readiness":
        print(json.dumps(verify_calibrated_readiness(arguments.preregistration, arguments.family, arguments.source_review), sort_keys=True))
        return 0
    if arguments.command == "calibrated-kernel-run":
        return calibrated_run(arguments.preregistration, arguments.output)
    if arguments.command == "calibrated-kernel-verify":
        return calibrated_verify(arguments.artifact)
    if arguments.command == "calibrated-kernel-replay":
        return calibrated_replay(arguments.artifact)
    if arguments.command == "calibrated-family-run":
        return calibrated_family_run(arguments.preregistration, arguments.family, arguments.source_review, arguments.output)
    if arguments.command == "calibrated-family-verify":
        return calibrated_family_verify(arguments.artifact)
    if arguments.command == "calibrated-family-replay":
        return calibrated_family_replay(arguments.artifact)
    print(json.dumps(verify_external_submission(arguments.submission, arguments.contract), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
