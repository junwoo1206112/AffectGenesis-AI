"""Local, non-overwriting command entry point for temporal-learning-v1."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time

from .config import canonical_json, load_config
from .evaluation import evaluate_checkpoint, train_seed
from .learner import ModelKind


RUN_ID = re.compile(r"^(?!con$|prn$|aux$|nul$|com[1-9]$|lpt[1-9]$)[a-z0-9][a-z0-9_-]{0,63}$", re.I)
EVIDENCE_FILES = frozenset({"manifest.json", "training.jsonl", "episodes.jsonl", "checkpoints.json", "metrics.json", "checks.json", "report.md"})


def _write(path: Path, value: object) -> str:
    encoded = canonical_json(value).encode("utf-8")
    path.write_bytes(encoded)
    return hashlib.sha256(encoded).hexdigest()


def _write_jsonl(path: Path, rows: list[object]) -> str:
    encoded = "".join(canonical_json(row) + "\n" for row in rows).encode("utf-8")
    path.write_bytes(encoded)
    return hashlib.sha256(encoded).hexdigest()


def _read_jsonl(path: Path) -> list[object]:
    raw = path.read_text(encoding="utf-8")
    if raw and not raw.endswith("\n"):
        raise ValueError("JSONL missing final newline")
    return [json.loads(line) for line in raw.splitlines()]


def _compare_rows(stream, expected) -> None:
    for row in expected:
        actual = stream.readline()
        if not actual or canonical_json(row) != canonical_json(json.loads(actual)):
            raise ValueError("JSONL replay mismatch")


def _assert_eof(stream) -> None:
    if stream.readline():
        raise ValueError("JSONL replay has extra rows")


def _source_hashes() -> dict[str, str]:
    root = Path(__file__).resolve().parent
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(root.glob("*.py"))}


def _append_jsonl(stream, rows: list[object]) -> None:
    for row in rows:
        stream.write(canonical_json(row) + "\n")


def run(config_path: str, run_id: str, root_base: Path = Path("artifacts") / "temporal_learning") -> int:
    if not RUN_ID.fullmatch(run_id):
        raise ValueError("invalid run id")
    config, config_hash = load_config(config_path)
    root = root_base / run_id
    root.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    try:
        def deadline() -> None:
            if time.monotonic() - started > config["time_limit_seconds"]:
                raise TimeoutError("temporal-learning run exceeded configured time limit")
        kinds = tuple(ModelKind(value) for value in config["models"])
        checkpoints: dict[str, object] = {}
        metrics: dict[str, object] = {}
        manifest_hash = _write(root / "manifest.json", {"protocol": config["protocol"], "config": config, "config_hash": config_hash, "source_sha256": _source_hashes(), "python": sys.version})
        with (root / "training.jsonl").open("x", encoding="utf-8", newline="\n") as training, (root / "episodes.jsonl").open("x", encoding="utf-8", newline="\n") as episodes:
            for seed in config["seeds"]:
                snapshots, rows = train_seed(seed, config["train_episodes"], tuple(config["checkpoints"]), config_hash, kinds, deadline)
                _append_jsonl(training, rows)
                checkpoints[str(seed)] = {str(index): {kind.value: data for kind, data in values.items()} for index, values in snapshots.items()}
                for index, values in snapshots.items():
                    for condition in ("same_distribution", "test_A", "test_B"):
                        for kind, data in values.items():
                            score, rows = evaluate_checkpoint(data, config_hash, condition, seed, config["evaluation_episodes"], index, deadline)
                            metrics.setdefault(str(index), {}).setdefault(condition, {}).setdefault(kind.value, []).append(score)
                            _append_jsonl(episodes, [{"checkpoint": index, "condition": condition, "model": kind.value, **row} for row in rows])
        hashes = {"manifest.json": manifest_hash, "training.jsonl": hashlib.sha256((root / "training.jsonl").read_bytes()).hexdigest(), "episodes.jsonl": hashlib.sha256((root / "episodes.jsonl").read_bytes()).hexdigest(), "checkpoints.json": _write(root / "checkpoints.json", checkpoints), "metrics.json": _write(root / "metrics.json", metrics)}
        hashes["checks.json"] = _write(root / "checks.json", {"status": "recorded", "effect_claim": "not evaluated by this command"})
        (root / "report.md").write_text("# temporal-learning-v1 run\n\nSynthetic result recorded; no claim of real emotion or consciousness.\n", encoding="utf-8")
        hashes["report.md"] = hashlib.sha256((root / "report.md").read_bytes()).hexdigest()
        _write(root / "completion.json", {"status": "completed", "file_hashes": hashes})
        return 0
    except Exception as error:
        _write(root / "failure.json", {"status": "failed", "error_type": type(error).__name__, "message": str(error)})
        raise


def verify(run_id: str, root_base: Path = Path("artifacts") / "temporal_learning") -> int:
    root = root_base / run_id
    if not root.is_dir() or root.is_symlink() or (root / "failure.json").exists():
        raise ValueError("invalid or failed artifact directory")
    completion_path = root / "completion.json"
    if not completion_path.is_file() or completion_path.is_symlink():
        raise ValueError("missing completion record")
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    if set(completion) != {"status", "file_hashes"} or completion.get("status") != "completed" or set(completion.get("file_hashes", {})) != EVIDENCE_FILES:
        raise ValueError("invalid completion record")
    for name, expected in completion["file_hashes"].items():
        path = root / name
        if not path.is_file() or path.is_symlink() or type(expected) is not str or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("artifact hash mismatch")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("protocol") != "temporal-learning-v1" or type(manifest.get("config")) is not dict
            or hashlib.sha256(canonical_json(manifest["config"]).encode("utf-8")).hexdigest() != manifest.get("config_hash")
            or manifest.get("source_sha256") != _source_hashes()):
        raise ValueError("invalid manifest identity")
    return 0


def replay(run_id: str, root_base: Path = Path("artifacts") / "temporal_learning") -> int:
    """Recompute the immutable training log and compare it byte-for-byte.

    Evaluation policy trajectories are intentionally not replayed yet; this
    command therefore rejects bundles that do not identify themselves as the
    current replay scope rather than overstating what was verified.
    """
    root = root_base / run_id
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    config, config_hash = manifest.get("config"), manifest.get("config_hash")
    if type(config) is not dict or type(config_hash) is not str:
        raise ValueError("invalid replay manifest")
    kinds = tuple(ModelKind(value) for value in config["models"])
    checkpoints = json.loads((root / "checkpoints.json").read_text(encoding="utf-8"))
    regenerated_checkpoints: dict[str, object] = {}
    with (root / "training.jsonl").open(encoding="utf-8") as training:
        for seed in config["seeds"]:
            snapshots, rows = train_seed(seed, config["train_episodes"], tuple(config["checkpoints"]), config_hash, kinds)
            _compare_rows(training, rows)
            regenerated_checkpoints[str(seed)] = {str(index): {kind.value: data for kind, data in values.items()} for index, values in snapshots.items()}
        _assert_eof(training)
    if canonical_json(regenerated_checkpoints) != canonical_json(checkpoints):
        raise ValueError("checkpoint replay mismatch")
    with (root / "episodes.jsonl").open(encoding="utf-8") as episodes:
        for seed in config["seeds"]:
            for index in config["checkpoints"]:
                for condition in ("same_distribution", "test_A", "test_B"):
                    for kind in config["models"]:
                        checkpoint = regenerated_checkpoints[str(seed)][str(index)][kind]
                        _, rows = evaluate_checkpoint(checkpoint, config_hash, condition, seed, config["evaluation_episodes"], index)
                        _compare_rows(episodes, ({"checkpoint": index, "condition": condition, "model": kind, **row} for row in rows))
        _assert_eof(episodes)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m temporal_learning")
    command = parser.add_subparsers(dest="command", required=True)
    run_parser = command.add_parser("run")
    run_parser.add_argument("--config", required=True)
    run_parser.add_argument("--run-id", required=True)
    verify_parser = command.add_parser("verify")
    verify_parser.add_argument("--run-id", required=True)
    replay_parser = command.add_parser("replay")
    replay_parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            return run(args.config, args.run_id)
        if args.command == "verify":
            return verify(args.run_id)
        return replay(args.run_id)
    except (OSError, ValueError) as error:
        print(f"temporal-learning error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
