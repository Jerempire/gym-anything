#!/usr/bin/env python3
from __future__ import annotations

from benchmarks.forecasting_world.shared import (
    SchemaValidationError,
    build_feedback,
    combine_weighted_scores,
    load_exported_forecast,
    load_exported_result,
    load_hidden_outcome,
    multiclass_probability_score,
    validate_submission,
)


def verify_soccer_match_outcome_distribution(traj, env_info, task_info):
    copy_from_env = env_info.get("copy_from_env")
    if not copy_from_env:
        return {"passed": False, "score": 0, "feedback": "Environment copy function unavailable"}

    metadata = task_info.get("metadata", {})
    feedback = []

    try:
        result = load_exported_result(copy_from_env)
    except Exception as exc:
        return {"passed": False, "score": 0, "feedback": f"Failed to load task result: {exc}"}

    if not result.get("forecast_exists"):
        return {"passed": False, "score": 0, "feedback": "Forecast file not found"}

    if not result.get("forecast_created_after_start"):
        return {"passed": False, "score": 0, "feedback": "Forecast file predates task start"}

    try:
        submission = load_exported_forecast(copy_from_env, result["forecast_path"])
        normalized = validate_submission(
            submission,
            expected_task_type=metadata["expected_task_type"],
            expected_target=metadata["expected_target"],
            expected_classes=metadata["expected_classes"],
        )
    except SchemaValidationError as exc:
        return {"passed": False, "score": 0, "feedback": f"Schema validation failed: {exc}"}
    except Exception as exc:
        return {"passed": False, "score": 0, "feedback": f"Failed to load forecast: {exc}"}

    if normalized["scenario_id"] != metadata["scenario_id"]:
        return {"passed": False, "score": 0, "feedback": "Scenario id does not match task metadata"}

    outcome = load_hidden_outcome(__file__, metadata["outcome_ref"])
    class_probabilities = normalized["forecast"]["class_probabilities"]
    actual_label = outcome["actual_label"]

    quality_score = multiclass_probability_score(class_probabilities, actual_label)
    completion_score = 100.0 if result.get("forecast_size", 0) > 0 else 0.0
    final_score = combine_weighted_scores(
        [
            (quality_score, 0.8),
            (completion_score, 0.2)
        ]
    )

    feedback.append(f"Actual result={actual_label}")
    feedback.append(f"Assigned probability={class_probabilities.get(actual_label, 0.0):.3f}")
    feedback.append(f"Forecast quality={quality_score:.1f}")

    return {
      "passed": final_score >= metadata.get("pass_threshold", 60),
      "score": round(final_score),
      "feedback": build_feedback(feedback)
    }
