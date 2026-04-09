from __future__ import annotations

import math
from typing import Iterable, Mapping


def clamp_probability(value: float, eps: float = 1e-9) -> float:
    return min(max(value, eps), 1.0 - eps)


def brier_score(probability: float, outcome: int) -> float:
    return (probability - float(outcome)) ** 2


def probability_score(probability: float, outcome: int) -> float:
    return max(0.0, 100.0 * (1.0 - brier_score(probability, outcome)))


def binary_log_loss(probability: float, outcome: int) -> float:
    probability = clamp_probability(probability)
    if outcome not in (0, 1):
        raise ValueError("outcome must be 0 or 1")
    return -(outcome * math.log(probability) + (1 - outcome) * math.log(1 - probability))


def multiclass_brier_score(
    class_probabilities: Mapping[str, float],
    actual_label: str,
) -> float:
    score = 0.0
    for label, probability in class_probabilities.items():
        target = 1.0 if label == actual_label else 0.0
        score += (probability - target) ** 2
    return score


def multiclass_probability_score(
    class_probabilities: Mapping[str, float],
    actual_label: str,
) -> float:
    return max(
        0.0,
        100.0 * (1.0 - min(multiclass_brier_score(class_probabilities, actual_label), 2.0) / 2.0),
    )


def recommended_binary_decision(
    probability: float,
    market_probability: float,
    *,
    threshold: float = 0.05,
) -> str:
    edge = probability - market_probability
    if edge >= threshold:
        return "long"
    if edge <= -threshold:
        return "short"
    return "abstain"


def decision_score(
    probability: float,
    market_probability: float,
    decision: str | None,
    *,
    threshold: float = 0.05,
) -> tuple[float, str]:
    recommended = recommended_binary_decision(
        probability,
        market_probability,
        threshold=threshold,
    )
    if decision is None:
        return (0.0, recommended)

    normalized_decision = decision.strip().lower()
    if normalized_decision == recommended:
        return (100.0, recommended)
    if recommended == "abstain" and normalized_decision in {"long", "short"}:
        return (0.0, recommended)
    if normalized_decision == "abstain":
        return (50.0, recommended)
    return (25.0, recommended)


def combine_weighted_scores(parts: Iterable[tuple[float, float]]) -> float:
    total_weight = 0.0
    total_score = 0.0
    for score, weight in parts:
        total_score += score * weight
        total_weight += weight
    if total_weight <= 0.0:
        raise ValueError("total weight must be positive")
    return total_score / total_weight
