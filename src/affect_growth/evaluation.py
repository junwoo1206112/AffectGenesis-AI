from __future__ import annotations

import hashlib
import json
import random
import re
import statistics
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from functional_affect.models import Action

from .environment import environment_contract, make_dataset, split_overlap_check
from .learner import Learner
from .models import ACTIONS, Case, Feedback, Observation
from .safety import safety_action


MODES = ("learned", "frozen", "memory")
METRICS = ("C", "A", "J")
ROOT = Path(__file__).resolve().parents[2]
EXPECTED_CONFIG = {
    "protocol": "growth-local-0.2", "seeds": list(range(10)),
    "train_count": 300, "dev_count": 100, "test_count": 100,
    "checkpoints": [0, 100, 200, 300],
    "orders": ["chronological", "shuffled"], "models": list(MODES),
    "alpha": 1.0, "confidence_threshold": 0.6,
    "frustration_decay": 0.8, "frustration_rate": 0.2,
    "action_modulation": {"decompose": -0.1, "clarify": 0.05, "replan_or_handoff": 0.05},
    "memory_neighbors": 5, "minimum_effect": 0.05, "positive_seeds": 8,
    "retention_tolerance": 0.01, "state_episodes": 10,
    "state_episode_length": 10, "time_limit_seconds": 600,
}


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_config(path: Path) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate configuration key")
            result[key] = value
        return result

    config = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    # One pre-registered pilot only; never silently ignore a changed parameter.
    if canonical(config) != canonical(EXPECTED_CONFIG):
        raise ValueError("Configuration differs from the fixed pilot protocol")
    return config


def score(model: Learner, cases: list[Case], reset: bool = True) -> dict:
    before = canonical(model.to_dict("evaluation"))
    worker = model.clone()
    if reset:
        worker.reset_state()
    groups: dict[int, list[tuple[int, int, int]]] = {}
    confusion = [[0] * 4 for _ in range(4)]
    records = []
    for case in cases:
        if safety_action(case.observation) is not None:
            raise ValueError("Safety cases cannot enter the learning metric denominator")
        prediction = worker.predict(case.observation)
        correct = int(prediction.label == case.target)
        appropriate = int(prediction.action in case.acceptable)
        groups.setdefault(case.family, []).append((correct, appropriate, correct * appropriate))
        confusion[case.target][prediction.label] += 1
        records.append({"family": case.family, "target": case.target,
                        "predicted": prediction.label, "action": prediction.action,
                        "allowed": list(case.acceptable), "cues": list(case.observation.cues)})
    if not groups:
        raise ValueError("Empty evaluation set")
    family_scores = {str(family): {key: statistics.mean(row[i] for row in rows)
                                 for i, key in enumerate(METRICS)}
                     for family, rows in sorted(groups.items())}
    if before != canonical(model.to_dict("evaluation")):
        raise RuntimeError("Evaluation mutated source checkpoint")
    return {**{key: statistics.mean(row[key] for row in family_scores.values()) for key in METRICS},
            "n": len(cases), "family_scores": family_scores,
            "confusion": confusion, "records": records}


def state_probe(model: Learner, cases: list[Case], seed: int) -> dict:
    """Exploratory fixed-log state intervention, never an on-policy outcome claim."""
    original = canonical(model.to_dict("probe"))
    rows = {key: [] for key in ("normal", "neutral", "permuted")}
    state_sequences = []
    for episode in range(10):
        chunk = cases[episode * 10:(episode + 1) * 10]
        if len(chunk) != 10:
            raise ValueError("State probe requires 100 development cases")
        worker = model.clone()
        worker.reset_state()
        states = []
        for case in chunk:
            states.append(worker.frustration)
            prediction = worker.predict(case.observation)
            rows["normal"].append((prediction.action, int(prediction.action in case.acceptable)))
            worker.learn(case.observation, case.feedback, update=False)
        shuffled = list(states)
        random.Random(seed * 100 + episode + 901).shuffle(shuffled)
        for name, values in (("neutral", [0.0] * 10), ("permuted", shuffled)):
            worker = model.clone()
            for case, f_value in zip(chunk, values):
                worker.frustration = f_value
                prediction = worker.predict(case.observation)
                rows[name].append((prediction.action, int(prediction.action in case.acceptable)))
                worker.learn(case.observation, case.feedback, update=False)
        state_sequences.append(states)
    if original != canonical(model.to_dict("probe")):
        raise RuntimeError("State probe mutated source checkpoint")
    normal = rows["normal"]
    return {
        "n": 100, "frustration_traces": state_sequences,
        "appropriateness": {key: statistics.mean(row[1] for row in values) for key, values in rows.items()},
        "action_change_rate": {key: statistics.mean(a[0] != b[0] for a, b in zip(normal, rows[key]))
                               for key in ("neutral", "permuted")},
        "claim": "exploratory_fixed_log_state_influence_not_felt_emotion_or_on_policy_benefit",
    }


def safety_sweep() -> dict:
    count = 0
    for mode in MODES:
        for parser in (False, True):
            for evidence in ((), ("synthetic",)):
                for urgent in (False, True):
                    for boundary in (False, True):
                        obs = Observation((0, 0, 0, 0), evidence, parser, urgent, boundary)
                        expected = safety_action(obs)
                        if expected is None:
                            continue
                        model = Learner(mode=mode)
                        before = canonical(model.to_dict("safety"))
                        if model.predict(obs).action != expected:
                            raise RuntimeError("Safety override violation")
                        model.learn(obs, Feedback(0, Action.DECOMPOSE, 1))
                        if before != canonical(model.to_dict("safety")):
                            raise RuntimeError("Safety case changed learning or state")
                        count += 1
    return {"cases": count, "violations": 0}


def summarize(rows: list[dict], probes: list[dict]) -> dict:
    selected = [row for row in rows if row["order"] == "chronological"]
    index = {(row["seed"], row["mode"], row["step"], row["reset"]): row for row in selected}
    contrasts = {}
    growth = True
    for comparison, mode, step in (("pre", "learned", 0), ("frozen", "frozen", 300), ("memory", "memory", 300)):
        contrasts[comparison] = {}
        for metric in METRICS:
            differences = [index[(seed, "learned", 300, True)][metric] - index[(seed, mode, step, True)][metric]
                           for seed in range(10)]
            mean = statistics.mean(differences)
            positives = sum(value > 0 for value in differences)
            passed = mean >= 0.05 and positives >= 8 if metric != "J" else mean > 0
            growth = growth and passed
            contrasts[comparison][metric] = {"paired": differences, "mean": mean,
                "min": min(differences), "max": max(differences), "sd": statistics.stdev(differences),
                "positive_seeds": positives, "passes": passed}
    retention = {}
    for metric in METRICS:
        drops = [index[(seed, "learned", 300, False)][metric] - index[(seed, "learned", 300, True)][metric]
                 for seed in range(10)]
        retention[metric] = {"drops": drops, "mean_drop": statistics.mean(drops),
                             "passes": statistics.mean(drops) <= 0.01}
    state_change = statistics.mean(p["action_change_rate"]["neutral"] for p in probes
                                   if p["mode"] == "learned" and p["order"] == "chronological")
    return {"growth_supported": growth and all(v["passes"] for v in retention.values()),
            "contrasts": contrasts, "retention": retention,
            "state_action_change_rate": state_change,
            "state_influence_observed": state_change > 0,
            "interpretation": "pilot_only; absence_of_growth_is_a_valid_result; no_claim_of_felt_emotion"}


def render_report(metrics: dict, evidence: str) -> str:
    result = metrics["summary"]
    lines = ["# 감정 성장 합성 실험 — 비교 평가", "", f"Evidence: {evidence}", "",
             "실제 사람 데이터·외부 LLM 없이 실행한 파일럿이다. 주관적 감정이나 인간 발달의 입증이 아니다.",
             "", f"- 프로토콜: {metrics['protocol']}",
             f"- 시드 수: 10; 시드별 순서 조건 2개, 학습 300건/조건, 평가 100건",
             f"- 안전 관문: {metrics['safety']['cases']}개 조건, 위반 {metrics['safety']['violations']}건",
             f"- 사전 기준에 따른 학습 가설: {'지지' if result['growth_supported'] else '미지지/불충분'}",
             f"- 탐색적 상태→행동 변화율: {result['state_action_change_rate']:.3%}", "",
             "## 학습 후 중립 상태의 paired 차이", "",
             "| 비교 대상 | 구별 C 평균 차이 | 대처 A 평균 차이 | 동시 J 평균 차이 |",
             "| --- | --- | --- | --- |"]
    # JSON canonicalization sorts mapping keys; report order must not depend on them.
    for label in ("pre", "frozen", "memory"):
        values = result["contrasts"][label]
        lines.append(f"| {label} | {values['C']['mean'] * 100:.2f}%p | {values['A']['mean'] * 100:.2f}%p | {values['J']['mean'] * 100:.2f}%p |")
    lines += ["", "C·A는 각 비교에서 평균 +5%p 및 8/10 시드 양수, J는 평균 양수가 사전 조건이다.",
              "전체 시드·family·혼동표·실패 사례·순서 대조는 metrics.json 및 episodes.jsonl에 보존했다.", "",
              "## 한계", "",
              "- 합성 지도 피드백과 설계된 상태 조절항을 사용한다. 자율 발달이나 생물학적 감정이 아니다.",
              "- 전이는 합성 단서 조합의 미학습 family에 한정한다. 실세계·유아기 전체로 일반화하지 않는다.",
              "- 상태 영향은 개발 로그 재생의 탐색 결과다. 선택 행동으로 더 좋은 실제 결과를 얻었다는 인과 주장이 아니다.",
              "- 실패 구간과 회복 구간은 분포를 설계한 조건이다. 기대 감소나 도움 요청 증가는 그 자체로 악화가 아니다.",
              "- 유지 판정은 일시 상태 초기화 및 저장·재로드 시험이다. 장기간 기억을 증명하지 않는다.",
              "- 10개 시드 파일럿과 실용 기준이며 검정력·통계적 유의성을 보장하지 않는다.",
              "- 구현 검증과 학습 가설 지지는 별개다. 미지지 결과를 숨기거나 기준을 낮추지 않았다.", ""]
    return "\n".join(lines)


def checked_run_dir(root: Path, run_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", run_id):
        raise ValueError("Unsafe run id")
    if run_id.lower() in {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}:
        raise ValueError("Reserved run id")
    root = root.resolve()
    target = root / "artifacts" / "affect_growth" / run_id
    for path in (root / "artifacts", root / "artifacts" / "affect_growth", target):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError("Linked output path is not allowed")
    if not target.resolve().is_relative_to(root):
        raise ValueError("Output path escape")
    if target.exists():
        raise FileExistsError("Run directory already exists; refusing overwrite")
    return target


def write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical(value) + "\n")


def run_experiment(config_path: Path, run_id: str, root: Path = ROOT) -> Path:
    config = load_config(config_path)
    config_hash = digest(config)
    target = checked_run_dir(root, run_id)
    target.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()

    def deadline():
        if time.monotonic() - started > config["time_limit_seconds"]:
            raise TimeoutError("Pilot exceeded its fixed time limit")

    try:
        datasets = {}
        for seed in config["seeds"]:
            datasets[seed] = {split: make_dataset(seed, split) for split in ("train", "dev", "test")}
            split_overlap_check(datasets[seed]["train"], datasets[seed]["dev"], datasets[seed]["test"])
        source_files = sorted((ROOT / "src" / "affect_growth").glob("*.py"))
        manifest = {"protocol": config["protocol"], "config": config, "config_hash": config_hash,
            "environment": environment_contract(), "started_utc": datetime.now(timezone.utc).isoformat(),
            "source_sha256": {str(path.relative_to(ROOT)).replace("\\", "/"): file_hash(path) for path in source_files},
            "data_sha256": {str(seed): {split: digest([asdict(case) for case in data]) for split, data in parts.items()}
                            for seed, parts in datasets.items()},
            "family_ids": {split: sorted({case.family for case in datasets[0][split]}) for split in ("train", "dev", "test")}}
        write_json(target / "manifest.json", manifest)
        rows, probes, checkpoints, ablations = [], [], [], []
        safety = safety_sweep()
        with (target / "episodes.jsonl").open("x", encoding="utf-8", newline="\n") as log:
            for seed, data in datasets.items():
                for split, cases in data.items():
                    for case in cases:
                        log.write(canonical({"kind": "dataset", "seed": seed, "split": split, "case": asdict(case)}) + "\n")
                for order in config["orders"]:
                    deadline()
                    train = list(data["train"])
                    if order == "shuffled":
                        random.Random(seed + 7001).shuffle(train)
                    models = {mode: Learner(mode=mode) for mode in MODES}
                    for step in range(301):
                        if step in config["checkpoints"]:
                            deadline()
                            for mode, model in models.items():
                                state = model.to_dict(config_hash)
                                restored = Learner.from_dict(state, config_hash)
                                if canonical(restored.to_dict(config_hash)) != canonical(state):
                                    raise RuntimeError("Checkpoint round-trip mismatch")
                                checkpoints.append({"seed": seed, "order": order, "mode": mode, "step": step, "state": state})
                                for reset in (True, False):
                                    result = score(restored, data["test"], reset=reset)
                                    rows.append({"seed": seed, "order": order, "mode": mode, "step": step,
                                                 "reset": reset, **result})
                                if step == 300:
                                    probes.append({"seed": seed, "order": order, "mode": mode,
                                                   **state_probe(restored, data["dev"], seed)})
                                    removed = Learner(mode=mode)
                                    removed.frustration = restored.frustration
                                    parameter_only = score(removed, data["test"], reset=False)
                                    removed.reset_state()
                                    full_reset = score(removed, data["test"], reset=False)
                                    initial = next(row for row in rows if row["seed"] == seed
                                                   and row["order"] == order and row["mode"] == mode
                                                   and row["step"] == 0 and row["reset"])
                                    if full_reset["records"] != initial["records"]:
                                        raise RuntimeError("Complete reset differs from initial model")
                                    ablations.append({"seed": seed, "order": order, "mode": mode,
                                        "parameter_only": parameter_only, "full_reset": full_reset,
                                        "initial_output_equal": True})
                        if step == 300:
                            break
                        case = train[step]
                        for mode, model in models.items():
                            before = model.frustration
                            p_logged = model.expected_success(case.observation, case.feedback.action)
                            model.learn(case.observation, case.feedback)
                            log.write(canonical({"kind": "learning", "seed": seed, "order": order,
                                "mode": mode, "step": step + 1, "case": asdict(case),
                                "p_logged": p_logged, "f_before": before, "f_after": model.frustration}) + "\n")
        metrics = {"protocol": config["protocol"], "config_hash": config_hash, "safety": safety,
                   "rows": rows, "state_probes": probes, "ablations": ablations,
                   "summary": summarize(rows, probes)}
        write_json(target / "checkpoints.json", checkpoints)
        write_json(target / "metrics.json", metrics)
        evidence = str(target.relative_to(root.resolve())).replace("\\", "/")
        with (target / "report.md").open("x", encoding="utf-8", newline="\n") as report:
            report.write(render_report(metrics, evidence))
        deadline()
        write_json(target / "completion.json", {"status": "completed",
            "files": {name: file_hash(target / name) for name in
                      ("manifest.json", "episodes.jsonl", "checkpoints.json", "metrics.json", "report.md")}})
        return target
    except Exception as error:
        write_json(target / "failure.json", {"status": "failed", "error_type": type(error).__name__, "message": str(error)})
        raise


def verify_report(report_path: Path, root: Path = ROOT) -> dict:
    root = root.resolve()
    text = report_path.read_text(encoding="utf-8")
    match = re.search(r"^Evidence: (artifacts/affect_growth/([A-Za-z0-9][A-Za-z0-9_-]{0,63}))$", text, re.MULTILINE)
    if not match:
        raise ValueError("Report has no safe evidence reference")
    target = root / match.group(1)
    for path in (root / "artifacts", root / "artifacts" / "affect_growth", target):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError("Linked evidence path")
    if not target.resolve().is_relative_to(root) or (target / "failure.json").exists():
        raise ValueError("Failed or escaped run")
    completion_path = target / "completion.json"
    if completion_path.is_symlink() or not completion_path.is_file():
        raise ValueError("Missing or linked completion record")
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    expected = {"manifest.json", "episodes.jsonl", "checkpoints.json", "metrics.json", "report.md"}
    if completion.get("status") != "completed" or set(completion.get("files", {})) != expected:
        raise ValueError("Incomplete evidence bundle")
    for name, checksum in completion["files"].items():
        path = target / name
        if path.is_symlink() or not path.is_file() or file_hash(path) != checksum:
            raise ValueError("Evidence digest mismatch")
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((target / "metrics.json").read_text(encoding="utf-8"))
    if canonical(manifest["config"]) != canonical(EXPECTED_CONFIG) or digest(manifest["config"]) != manifest["config_hash"]:
        raise ValueError("Invalid manifest configuration")
    if metrics["config_hash"] != manifest["config_hash"] or metrics["safety"]["violations"] != 0:
        raise ValueError("Invalid metrics or unsafe run")
    validate_evidence_metrics(metrics)
    for name, checksum in manifest["source_sha256"].items():
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT / "src" / "affect_growth") or file_hash(path) != checksum:
            raise ValueError("Source code differs from the recorded experiment")
    for seed in range(10):
        for split in ("train", "dev", "test"):
            expected_hash = digest([asdict(case) for case in make_dataset(seed, split)])
            if manifest["data_sha256"][str(seed)][split] != expected_hash:
                raise ValueError("Dataset hash differs from the fixed generator")
    checkpoints = json.loads((target / "checkpoints.json").read_text(encoding="utf-8"))
    expected_keys = {(seed, order, mode, step) for seed in range(10)
                     for order in EXPECTED_CONFIG["orders"] for mode in MODES
                     for step in EXPECTED_CONFIG["checkpoints"]}
    if len(checkpoints) != len(expected_keys) or {
        (row["seed"], row["order"], row["mode"], row["step"]) for row in checkpoints
    } != expected_keys:
        raise ValueError("Missing or duplicate checkpoints")
    for row in checkpoints:
        model = Learner.from_dict(row["state"], manifest["config_hash"])
        if model.mode != row["mode"]:
            raise ValueError("Checkpoint mode mismatch")
    if canonical(summarize(metrics["rows"], metrics["state_probes"])) != canonical(metrics["summary"]):
        raise ValueError("Summary does not match paired observations")
    if text != render_report(metrics, match.group(1)):
        raise ValueError("Report text does not match evidence")
    return metrics["summary"]


def validate_evidence_metrics(metrics: dict) -> None:
    """Check evidence structure and recompute scores from per-case decisions.

    This is an integrity check, not a digital signature or independent rerun of training.
    """
    rows = metrics["rows"]
    expected_keys = {(seed, order, mode, step, reset) for seed in range(10)
                     for order in EXPECTED_CONFIG["orders"] for mode in MODES
                     for step in EXPECTED_CONFIG["checkpoints"] for reset in (True, False)}
    keys = [(r["seed"], r["order"], r["mode"], r["step"], r["reset"]) for r in rows]
    if len(keys) != len(expected_keys) or set(keys) != expected_keys:
        raise ValueError("Missing or duplicate evaluation rows")
    for row in rows:
        cases = make_dataset(row["seed"], "test")
        if row["n"] != 100 or len(row["records"]) != 100:
            raise ValueError("Invalid metric denominator")
        groups = {}
        confusion = [[0] * 4 for _ in range(4)]
        for record, case in zip(row["records"], cases):
            if (record["family"] != case.family or record["target"] != case.target
                    or record["cues"] != list(case.observation.cues)
                    or record["allowed"] != list(case.acceptable)
                    or type(record["predicted"]) is not int or record["predicted"] not in range(4)
                    or record["action"] not in ACTIONS):
                raise ValueError("Case evidence does not match fixed evaluation")
            c = int(record["predicted"] == case.target)
            a = int(record["action"] in case.acceptable)
            groups.setdefault(str(case.family), []).append((c, a, c * a))
            confusion[case.target][record["predicted"]] += 1
        family = {key: {metric: statistics.mean(r[i] for r in values) for i, metric in enumerate(METRICS)}
                  for key, values in groups.items()}
        if family != row["family_scores"] or confusion != row["confusion"]:
            raise ValueError("Derived family scores or confusion mismatch")
        for metric in METRICS:
            if statistics.mean(value[metric] for value in family.values()) != row[metric]:
                raise ValueError("Metric does not match case evidence")
    condition_keys = {(seed, order, mode) for seed in range(10) for order in EXPECTED_CONFIG["orders"] for mode in MODES}
    for name in ("state_probes", "ablations"):
        values = metrics[name]
        if len(values) != len(condition_keys) or {(r["seed"], r["order"], r["mode"]) for r in values} != condition_keys:
            raise ValueError("Missing or duplicate intervention rows")
    if not all(row["initial_output_equal"] is True for row in metrics["ablations"]):
        raise ValueError("Complete-reset check failed")
