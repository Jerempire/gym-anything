from __future__ import annotations

import unittest

from benchmarks.forecasting_world.shared.scoring import (
    combine_weighted_scores,
    decision_score,
    multiclass_probability_score,
    probability_score,
    recommended_binary_decision,
)
from benchmarks.forecasting_world.shared.schemas import (
    SchemaValidationError,
    validate_submission,
)


class ForecastingScoringTests(unittest.TestCase):
    def test_binary_probability_score_rewards_better_forecasts(self) -> None:
        self.assertGreater(probability_score(0.8, 1), probability_score(0.6, 1))
        self.assertGreater(probability_score(0.2, 0), probability_score(0.4, 0))

    def test_multiclass_probability_score_rewards_mass_on_true_label(self) -> None:
        strong = multiclass_probability_score({"low": 0.1, "medium": 0.2, "high": 0.7}, "high")
        weak = multiclass_probability_score({"low": 0.4, "medium": 0.3, "high": 0.3}, "high")
        self.assertGreater(strong, weak)

    def test_recommended_binary_decision_uses_threshold(self) -> None:
        self.assertEqual(recommended_binary_decision(0.66, 0.50), "long")
        self.assertEqual(recommended_binary_decision(0.34, 0.50), "short")
        self.assertEqual(recommended_binary_decision(0.53, 0.50), "abstain")

    def test_decision_score_rewards_matching_action(self) -> None:
        score, recommended = decision_score(0.66, 0.50, "long")
        self.assertEqual(recommended, "long")
        self.assertEqual(score, 100.0)

    def test_combine_weighted_scores_returns_weighted_average(self) -> None:
        combined = combine_weighted_scores([(100.0, 0.75), (50.0, 0.25)])
        self.assertEqual(combined, 87.5)


class ForecastingSchemaTests(unittest.TestCase):
    def test_validate_binary_submission(self) -> None:
        normalized = validate_submission(
            {
                "scenario_id": "markets.es.2026-001",
                "task_type": "binary_probability",
                "forecast": {
                    "target": "next_session_up",
                    "probability": 0.61
                },
                "confidence": 0.7
            },
            expected_task_type="binary_probability",
            expected_target="next_session_up",
        )
        self.assertEqual(normalized["forecast"]["probability"], 0.61)

    def test_validate_multiclass_submission(self) -> None:
        normalized = validate_submission(
            {
                "scenario_id": "markets.nq.2026-002",
                "task_type": "multiclass_distribution",
                "forecast": {
                    "target": "next_session_volatility_regime",
                    "class_probabilities": {
                        "low": 0.2,
                        "medium": 0.5,
                        "high": 0.3
                    }
                }
            },
            expected_task_type="multiclass_distribution",
            expected_target="next_session_volatility_regime",
            expected_classes=["low", "medium", "high"],
        )
        self.assertEqual(normalized["forecast"]["class_probabilities"]["medium"], 0.5)

    def test_invalid_probability_sum_raises(self) -> None:
        with self.assertRaises(SchemaValidationError):
            validate_submission(
                {
                    "scenario_id": "markets.nq.2026-002",
                    "task_type": "multiclass_distribution",
                    "forecast": {
                        "target": "next_session_volatility_regime",
                        "class_probabilities": {
                            "low": 0.2,
                            "medium": 0.5,
                            "high": 0.4
                        }
                    }
                },
                expected_task_type="multiclass_distribution",
                expected_target="next_session_volatility_regime",
                expected_classes=["low", "medium", "high"],
            )


if __name__ == "__main__":
    unittest.main()
