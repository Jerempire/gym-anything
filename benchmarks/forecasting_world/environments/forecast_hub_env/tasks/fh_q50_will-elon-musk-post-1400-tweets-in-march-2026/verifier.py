#!/usr/bin/env python3
from __future__ import annotations

from benchmarks.forecasting_world.shared import (
    SchemaValidationError,
    build_feedback,
    combine_weighted_scores,
    decision_score,
    load_exported_forecast,
    load_exported_result,
    load_hidden_outcome,
    probability_score,
    validate_submission,
)


def verify_imported_forecast_hub_task(traj, env_info, task_info):
    copy_from_env = env_info.get("copy_from_env")
    if not copy_from_env:
        return {{"passed": False, "score": 0, "feedback": "Environment copy function unavailable"}}

    metadata = task_info.get("metadata", {{}})
    feedback = []
    try:
        result = load_exported_result(copy_from_env)
    except Exception as exc:
        return {{"passed": False, "score": 0, "feedback": f"Failed to load task result: {{exc}}" }}

    if not result.get("forecast_exists"):
        return {{"passed": False, "score": 0, "feedback": "Forecast file not found"}}
    if not result.get("forecast_created_after_start"):
        return {{"passed": False, "score": 0, "feedback": "Forecast file predates task start"}}

    try:
        submission = load_exported_forecast(copy_from_env, result["forecast_path"])
        normalized = validate_submission(
            submission,
            expected_task_type=metadata["expected_task_type"],
            expected_target=metadata["expected_target"],
        )
    except SchemaValidationError as exc:
        return {{"passed": False, "score": 0, "feedback": f"Schema validation failed: {{exc}}" }}
    except Exception as exc:
        return {{"passed": False, "score": 0, "feedback": f"Failed to load forecast: {{exc}}" }}

    if normalized["scenario_id"] != metadata["scenario_id"]:
        return {{"passed": False, "score": 0, "feedback": "Scenario id does not match task metadata"}}

    outcome = load_hidden_outcome(__file__, metadata["outcome_ref"])
    forecast_probability = normalized["forecast"]["probability"]
    outcome_value = int(outcome["outcome"])
    quality_score = probability_score(forecast_probability, outcome_value)
    completion_score = 100.0 if result.get("forecast_size", 0) > 0 else 0.0

    decision_quality = None
    if "market_implied_probability" in outcome and outcome["market_implied_probability"] is not None:
        decision_quality, recommended_action = decision_score(
            forecast_probability,
            float(outcome["market_implied_probability"]),
            normalized.get("decision"),
            threshold=float(outcome.get("decision_threshold", 0.05)),
        )
        final_score = combine_weighted_scores([(quality_score, 0.7), (decision_quality, 0.2), (completion_score, 0.1)])
        feedback.append(f"Decision={{normalized.get('decision') or 'missing'}}")
        feedback.append(f"Recommended action={{recommended_action}}")
        feedback.append(f"Decision quality={{decision_quality:.1f}}")
    else:
        final_score = combine_weighted_scores([(quality_score, 0.85), (completion_score, 0.15)])

    feedback.append(f"Probability={{forecast_probability:.3f}}")
    feedback.append(f"Outcome={{outcome_value}}")
    feedback.append(f"Forecast quality={{quality_score:.1f}}")
    return {{
        "passed": final_score >= metadata.get("pass_threshold", 65),
        "score": round(final_score),
        "feedback": build_feedback(feedback),
    }}
