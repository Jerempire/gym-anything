from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from benchmarks.forecasting_world.registry import (
    get_tasks_for_environment,
    load_environment_task_splits,
    resolve_environment_dir,
)
from benchmarks.forecasting_world.shared import (
    SchemaValidationError,
    combine_weighted_scores,
    decision_score,
    load_hidden_outcome,
    multiclass_probability_score,
    probability_score,
    validate_submission,
)


@dataclass
class ForecastTaskReport:
    env_name: str
    task_id: str
    scenario_id: Optional[str]
    task_type: Optional[str]
    score: float
    passed: bool
    submission_path: Optional[str] = None
    forecast_quality: Optional[float] = None
    decision_quality: Optional[float] = None
    forecast_probability: Optional[float] = None
    actual_outcome: Optional[int] = None
    market_probability: Optional[float] = None
    expected_decision: Optional[str] = None
    source_probability: Optional[float] = None
    source_label: Optional[str] = None
    source_score: Optional[float] = None
    source_edge: Optional[float] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ForecastBatchReport:
    submission_root: str
    split: str
    task_reports: List[ForecastTaskReport] = field(default_factory=list)
    binary_calibration: List[Dict[str, Any]] = field(default_factory=list)
    by_environment: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    source_comparison: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_tasks(self) -> int:
        return len(self.task_reports)

    @property
    def scored_tasks(self) -> int:
        return sum(1 for report in self.task_reports if report.error is None)

    @property
    def failed_tasks(self) -> int:
        return sum(1 for report in self.task_reports if not report.passed)

    @property
    def average_score(self) -> float:
        scores = [report.score for report in self.task_reports if report.error is None]
        return sum(scores) / len(scores) if scores else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "submission_root": self.submission_root,
            "split": self.split,
            "total_tasks": self.total_tasks,
            "scored_tasks": self.scored_tasks,
            "failed_tasks": self.failed_tasks,
            "average_score": self.average_score,
            "binary_calibration": self.binary_calibration,
            "by_environment": self.by_environment,
            "source_comparison": self.source_comparison,
            "task_reports": [report.to_dict() for report in self.task_reports],
        }


def _iter_env_task_pairs(env_filter: Optional[str], split: str) -> Iterable[tuple[str, Path, str]]:
    registry = load_environment_task_splits()
    if env_filter:
        env_dir = resolve_environment_dir(env_filter)
        env_name = env_dir.name
        tasks = get_tasks_for_environment(env_name, split=split)
        for task_id in tasks:
            yield env_name, env_dir, task_id
        return

    for env_name, split_map in registry.items():
        if split not in split_map:
            continue
        env_dir = resolve_environment_dir(env_name)
        for task_id in split_map[split]:
            yield env_name, env_dir, task_id


def _find_submission_path(submission_root: Path, env_name: str, task_id: str) -> Optional[Path]:
    candidates = [
        submission_root / env_name / f"{task_id}.json",
        submission_root / env_name / task_id / "submission.json",
        submission_root / f"{task_id}.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _load_json(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_source_probability(
    task_dir: Path,
    outcome: Mapping[str, Any],
) -> tuple[Optional[float], Optional[str]]:
    def normalize(value: Any, label: str) -> tuple[Optional[float], Optional[str]]:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return (None, None)
        probability = float(value)
        if 0.0 <= probability <= 1.0:
            return (probability, label)
        return (None, None)

    direct_sources = [
        (outcome.get("market_implied_probability"), "market_implied_probability"),
    ]
    for value, label in direct_sources:
        probability, normalized_label = normalize(value, label)
        if probability is not None:
            return (probability, normalized_label)

    scenario_path = task_dir / "scenario.json"
    if not scenario_path.exists():
        return (None, None)

    try:
        scenario = _load_json(scenario_path)
    except Exception:
        return (None, None)

    scenario_sources = [
        (scenario.get("latest_market_probability"), "latest_market_probability"),
        (scenario.get("last_trade_price"), "last_trade_price"),
        (scenario.get("confidence"), "signal_confidence"),
        (scenario.get("prior_positive_rate"), "prior_positive_rate"),
    ]
    for value, label in scenario_sources:
        probability, normalized_label = normalize(value, label)
        if probability is not None:
            return (probability, normalized_label)

    best_bid = scenario.get("best_bid")
    best_ask = scenario.get("best_ask")
    if isinstance(best_bid, (int, float)) and isinstance(best_ask, (int, float)):
        midpoint = (float(best_bid) + float(best_ask)) / 2.0
        probability, normalized_label = normalize(midpoint, "mid_quote")
        if probability is not None:
            return (probability, normalized_label)

    return (None, None)


def _evaluate_submission(
    *,
    env_name: str,
    task_dir: Path,
    task_id: str,
    submission_path: Optional[Path],
) -> ForecastTaskReport:
    task_spec = _load_json(task_dir / "task.json")
    metadata = task_spec.get("metadata", {})
    scenario_id = metadata.get("scenario_id")
    expected_task_type = metadata.get("expected_task_type")

    if submission_path is None:
        return ForecastTaskReport(
            env_name=env_name,
            task_id=task_id,
            scenario_id=scenario_id,
            task_type=expected_task_type,
            score=0.0,
            passed=False,
            error="submission not found",
        )

    try:
        submission = _load_json(submission_path)
        normalized = validate_submission(
            submission,
            expected_task_type=metadata["expected_task_type"],
            expected_target=metadata.get("expected_target"),
            expected_classes=metadata.get("expected_classes"),
        )
        if normalized["scenario_id"] != metadata["scenario_id"]:
            raise SchemaValidationError("scenario_id does not match task metadata")
        outcome = load_hidden_outcome(task_dir / "verifier.py", metadata["outcome_ref"])
    except Exception as exc:
        return ForecastTaskReport(
            env_name=env_name,
            task_id=task_id,
            scenario_id=scenario_id,
            task_type=expected_task_type,
            score=0.0,
            passed=False,
            submission_path=str(submission_path),
            error=str(exc),
        )

    forecast_quality: float
    decision_quality: Optional[float] = None
    forecast_probability: Optional[float] = None
    actual_outcome: Optional[int] = None
    market_probability: Optional[float] = None
    expected_decision: Optional[str] = None
    source_probability: Optional[float] = None
    source_label: Optional[str] = None
    source_score: Optional[float] = None
    source_edge: Optional[float] = None
    if expected_task_type == "binary_probability":
        forecast_probability = normalized["forecast"]["probability"]
        outcome_value = int(outcome["outcome"])
        actual_outcome = outcome_value
        forecast_quality = probability_score(forecast_probability, outcome_value)
        source_probability, source_label = _extract_source_probability(task_dir, outcome)
        if source_probability is not None:
            source_score = probability_score(source_probability, outcome_value)
            source_edge = forecast_quality - source_score
        if "market_implied_probability" in outcome:
            market_probability = float(outcome["market_implied_probability"])
            decision_quality, _recommended = decision_score(
                forecast_probability,
                market_probability,
                normalized.get("decision"),
                threshold=float(outcome.get("decision_threshold", 0.05)),
            )
            expected_decision = _recommended
    elif expected_task_type == "multiclass_distribution":
        forecast_quality = multiclass_probability_score(
            normalized["forecast"]["class_probabilities"],
            outcome["actual_label"],
        )
    else:
        return ForecastTaskReport(
            env_name=env_name,
            task_id=task_id,
            scenario_id=scenario_id,
            task_type=expected_task_type,
            score=0.0,
            passed=False,
            submission_path=str(submission_path),
            error=f"unsupported task type: {expected_task_type}",
        )

    if decision_quality is not None:
        score = combine_weighted_scores([(forecast_quality, 0.75), (decision_quality, 0.25)])
    else:
        score = forecast_quality

    return ForecastTaskReport(
        env_name=env_name,
        task_id=task_id,
        scenario_id=scenario_id,
        task_type=expected_task_type,
        score=round(score, 2),
        passed=score >= float(metadata.get("pass_threshold", 60)),
        submission_path=str(submission_path),
        forecast_quality=round(forecast_quality, 2),
        decision_quality=round(decision_quality, 2) if decision_quality is not None else None,
        forecast_probability=forecast_probability,
        actual_outcome=actual_outcome,
        market_probability=market_probability,
        expected_decision=expected_decision,
        source_probability=round(source_probability, 4) if source_probability is not None else None,
        source_label=source_label,
        source_score=round(source_score, 2) if source_score is not None else None,
        source_edge=round(source_edge, 2) if source_edge is not None else None,
    )


def _build_environment_summary(task_reports: Iterable[ForecastTaskReport]) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, List[ForecastTaskReport]] = {}
    for report in task_reports:
        grouped.setdefault(report.env_name, []).append(report)

    summary: Dict[str, Dict[str, Any]] = {}
    for env_name, reports in grouped.items():
        scored = [report.score for report in reports if report.error is None]
        forecast_scores = [
            report.forecast_quality for report in reports
            if report.error is None and report.forecast_quality is not None
        ]
        decision_scores = [
            report.decision_quality for report in reports
            if report.error is None and report.decision_quality is not None
        ]
        summary[env_name] = {
            "total_tasks": len(reports),
            "scored_tasks": len(scored),
            "failed_tasks": sum(1 for report in reports if not report.passed),
            "average_score": (sum(scored) / len(scored)) if scored else 0.0,
            "average_forecast_quality": (
                sum(forecast_scores) / len(forecast_scores) if forecast_scores else None
            ),
            "average_decision_quality": (
                sum(decision_scores) / len(decision_scores) if decision_scores else None
            ),
            "source_comparable_tasks": sum(1 for report in reports if report.source_score is not None),
            "average_source_score": (
                sum(report.source_score for report in reports if report.source_score is not None)
                / sum(1 for report in reports if report.source_score is not None)
                if any(report.source_score is not None for report in reports)
                else None
            ),
            "average_model_edge_vs_source": (
                sum(report.source_edge for report in reports if report.source_edge is not None)
                / sum(1 for report in reports if report.source_edge is not None)
                if any(report.source_edge is not None for report in reports)
                else None
            ),
        }
    return summary


def _build_source_comparison(task_reports: Iterable[ForecastTaskReport]) -> Dict[str, Any]:
    comparable = [
        report for report in task_reports
        if report.error is None and report.source_score is not None and report.source_edge is not None
    ]
    if not comparable:
        return {
            "comparable_tasks": 0,
            "average_source_score": None,
            "average_model_edge": None,
            "win_rate_vs_source": None,
        }
    comparable_count = len(comparable)
    return {
        "comparable_tasks": comparable_count,
        "average_source_score": sum(report.source_score for report in comparable) / comparable_count,
        "average_model_edge": sum(report.source_edge for report in comparable) / comparable_count,
        "win_rate_vs_source": (
            sum(1 for report in comparable if (report.source_edge or 0.0) > 0.0) / comparable_count
        ),
    }


def _build_binary_calibration(task_reports: Iterable[ForecastTaskReport]) -> List[Dict[str, Any]]:
    bins = [
        {
            "start": i / 10,
            "end": (i + 1) / 10,
            "count": 0,
            "average_predicted": None,
            "observed_frequency": None,
        }
        for i in range(10)
    ]
    for report in task_reports:
        if (
            report.task_type != "binary_probability"
            or report.error is not None
            or report.forecast_probability is None
            or report.actual_outcome is None
        ):
            continue
        bucket = min(int(report.forecast_probability * 10), 9)
        entry = bins[bucket]
        entry["count"] += 1
        entry.setdefault("_predicted_sum", 0.0)
        entry.setdefault("_observed_sum", 0.0)
        entry["_predicted_sum"] += report.forecast_probability
        entry["_observed_sum"] += report.actual_outcome
    for entry in bins:
        count = entry["count"]
        if count:
            entry["average_predicted"] = round(entry.pop("_predicted_sum") / count, 4)
            entry["observed_frequency"] = round(entry.pop("_observed_sum") / count, 4)
        else:
            entry.pop("_predicted_sum", None)
            entry.pop("_observed_sum", None)
    return bins


def build_forecast_batch_report(
    submission_root: str | Path,
    *,
    env_filter: Optional[str] = None,
    split: str = "all",
) -> ForecastBatchReport:
    submission_root = Path(submission_root)
    task_reports: List[ForecastTaskReport] = []
    for env_name, env_dir, task_id in _iter_env_task_pairs(env_filter, split):
        task_dir = env_dir / "tasks" / task_id
        submission_path = _find_submission_path(submission_root, env_name, task_id)
        task_reports.append(
            _evaluate_submission(
                env_name=env_name,
                task_dir=task_dir,
                task_id=task_id,
                submission_path=submission_path,
            )
        )

    return ForecastBatchReport(
        submission_root=str(submission_root),
        split=split,
        task_reports=task_reports,
        binary_calibration=_build_binary_calibration(task_reports),
        by_environment=_build_environment_summary(task_reports),
        source_comparison=_build_source_comparison(task_reports),
    )


def render_forecast_batch_report_text(report: ForecastBatchReport) -> str:
    lines = [
        f"Submission root: {report.submission_root}",
        f"Split: {report.split}",
        f"Total tasks: {report.total_tasks}",
        f"Scored tasks: {report.scored_tasks}",
        f"Failed tasks: {report.failed_tasks}",
        f"Average score: {report.average_score:.2f}",
    ]
    for env_name, summary in sorted(report.by_environment.items()):
        detail = (
            f"[{env_name}] total={summary['total_tasks']} scored={summary['scored_tasks']} "
            f"failed={summary['failed_tasks']} avg={summary['average_score']:.2f}"
        )
        if summary["average_forecast_quality"] is not None:
            detail += f" forecast={summary['average_forecast_quality']:.2f}"
        if summary["average_decision_quality"] is not None:
            detail += f" decision={summary['average_decision_quality']:.2f}"
        if summary["average_source_score"] is not None:
            detail += f" source={summary['average_source_score']:.2f}"
        if summary["average_model_edge_vs_source"] is not None:
            detail += f" edge={summary['average_model_edge_vs_source']:+.2f}"
        lines.append(detail)
    if report.source_comparison.get("comparable_tasks"):
        lines.append(
            "Source priors: "
            f"n={report.source_comparison['comparable_tasks']} "
            f"avg_source={report.source_comparison['average_source_score']:.2f} "
            f"avg_edge={report.source_comparison['average_model_edge']:+.2f} "
            f"win_rate={report.source_comparison['win_rate_vs_source']:.2%}"
        )
    if any(bucket["count"] for bucket in report.binary_calibration):
        lines.append("Binary calibration:")
        for bucket in report.binary_calibration:
            if not bucket["count"]:
                continue
            lines.append(
                f"  {bucket['start']:.1f}-{bucket['end']:.1f}: n={bucket['count']} "
                f"pred={bucket['average_predicted']:.3f} obs={bucket['observed_frequency']:.3f}"
            )
    for task_report in report.task_reports:
        status = "OK" if task_report.passed else "FAIL"
        detail = f"[{status}] {task_report.env_name}/{task_report.task_id} score={task_report.score:.2f}"
        if task_report.error:
            detail += f" error={task_report.error}"
        elif task_report.source_score is not None and task_report.source_edge is not None:
            detail += (
                f" source={task_report.source_label}:{task_report.source_probability:.3f}"
                f" source_score={task_report.source_score:.2f}"
                f" edge={task_report.source_edge:+.2f}"
            )
        lines.append(detail)
    return "\n".join(lines)


__all__ = [
    "ForecastBatchReport",
    "ForecastTaskReport",
    "build_forecast_batch_report",
    "render_forecast_batch_report_text",
]
