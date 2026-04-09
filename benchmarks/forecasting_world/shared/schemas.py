from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping


class SchemaValidationError(ValueError):
    """Raised when a forecast submission does not match the expected schema."""


def _require_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(f"{field_name} must be an object")
    return value


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_number(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SchemaValidationError(f"{field_name} must be a number")
    return float(value)


def _require_probability(value: Any, field_name: str) -> float:
    probability = _require_number(value, field_name)
    if probability < 0.0 or probability > 1.0:
        raise SchemaValidationError(f"{field_name} must be between 0 and 1")
    return probability


def _normalize_optional_probability(value: Any, field_name: str) -> float | None:
    if value is None:
        return None
    return _require_probability(value, field_name)


def _normalize_optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_string(value, field_name)


def _normalize_optional_number(value: Any, field_name: str) -> float | None:
    if value is None:
        return None
    return _require_number(value, field_name)


def _validate_binary_probability(
    payload: Mapping[str, Any],
    *,
    expected_target: str | None = None,
) -> Dict[str, Any]:
    forecast = _require_mapping(payload.get("forecast"), "forecast")
    target = _require_string(forecast.get("target"), "forecast.target")
    probability = _require_probability(forecast.get("probability"), "forecast.probability")
    if expected_target is not None and target != expected_target:
        raise SchemaValidationError(
            f"forecast.target must be {expected_target!r}, got {target!r}"
        )

    normalized = {
        "scenario_id": _require_string(payload.get("scenario_id"), "scenario_id"),
        "task_type": "binary_probability",
        "forecast": {
            "target": target,
            "probability": probability,
        },
        "confidence": _normalize_optional_probability(payload.get("confidence"), "confidence"),
        "decision": _normalize_optional_string(payload.get("decision"), "decision"),
        "stake_fraction": _normalize_optional_number(payload.get("stake_fraction"), "stake_fraction"),
        "notes": _normalize_optional_string(payload.get("notes"), "notes"),
    }
    if normalized["stake_fraction"] is not None:
        if normalized["stake_fraction"] < 0.0 or normalized["stake_fraction"] > 1.0:
            raise SchemaValidationError("stake_fraction must be between 0 and 1")
    return normalized


def _validate_multiclass_distribution(
    payload: Mapping[str, Any],
    *,
    expected_target: str | None = None,
    expected_classes: Iterable[str] | None = None,
) -> Dict[str, Any]:
    forecast = _require_mapping(payload.get("forecast"), "forecast")
    target = _require_string(forecast.get("target"), "forecast.target")
    if expected_target is not None and target != expected_target:
        raise SchemaValidationError(
            f"forecast.target must be {expected_target!r}, got {target!r}"
        )

    raw_probs = _require_mapping(forecast.get("class_probabilities"), "forecast.class_probabilities")
    class_probabilities: Dict[str, float] = {}
    for class_name, probability in raw_probs.items():
        normalized_name = _require_string(class_name, "forecast.class_probabilities key")
        class_probabilities[normalized_name] = _require_probability(
            probability,
            f"forecast.class_probabilities.{normalized_name}",
        )

    if not class_probabilities:
        raise SchemaValidationError("forecast.class_probabilities must not be empty")

    total_probability = sum(class_probabilities.values())
    if abs(total_probability - 1.0) > 1e-6:
        raise SchemaValidationError(
            f"forecast.class_probabilities must sum to 1.0, got {total_probability:.6f}"
        )

    if expected_classes is not None:
        expected_set = set(expected_classes)
        actual_set = set(class_probabilities)
        if actual_set != expected_set:
            raise SchemaValidationError(
                f"forecast.class_probabilities keys must match {sorted(expected_set)!r}, "
                f"got {sorted(actual_set)!r}"
            )

    return {
        "scenario_id": _require_string(payload.get("scenario_id"), "scenario_id"),
        "task_type": "multiclass_distribution",
        "forecast": {
            "target": target,
            "class_probabilities": class_probabilities,
        },
        "confidence": _normalize_optional_probability(payload.get("confidence"), "confidence"),
        "decision": _normalize_optional_string(payload.get("decision"), "decision"),
        "stake_fraction": _normalize_optional_number(payload.get("stake_fraction"), "stake_fraction"),
        "notes": _normalize_optional_string(payload.get("notes"), "notes"),
    }


def validate_submission(
    payload: Mapping[str, Any],
    *,
    expected_task_type: str,
    expected_target: str | None = None,
    expected_classes: Iterable[str] | None = None,
) -> Dict[str, Any]:
    payload_task_type = payload.get("task_type")
    if payload_task_type is not None and payload_task_type != expected_task_type:
        raise SchemaValidationError(
            f"task_type must be {expected_task_type!r}, got {payload_task_type!r}"
        )
    if expected_task_type == "binary_probability":
        return _validate_binary_probability(payload, expected_target=expected_target)
    if expected_task_type == "multiclass_distribution":
        return _validate_multiclass_distribution(
            payload,
            expected_target=expected_target,
            expected_classes=expected_classes,
        )
    raise SchemaValidationError(f"Unsupported expected_task_type: {expected_task_type}")
