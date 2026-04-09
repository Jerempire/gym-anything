from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from benchmarks.forecasting_world.evaluation import reporting
from benchmarks.forecasting_world.evaluation import (
    build_forecast_batch_report,
    render_forecast_batch_report_text,
)


class ForecastingReportingTests(unittest.TestCase):
    def test_batch_report_scores_binary_and_multiclass_submissions(self) -> None:
        real_load_json = reporting._load_json

        def fake_find_submission_path(_submission_root: Path, _env_name: str, task_id: str):
            if task_id in {
                "es_next_session_probability",
                "soccer_match_outcome_distribution",
                "ff_sig317_20260407_cvd-divergence_long",
                "pm_m516710_us-recession-in-2025",
            }:
                return Path(f"/virtual/{task_id}.json")
            return None

        def fake_load_json(path: Path):
            name = Path(path).name
            if name == "es_next_session_probability.json":
                return {
                    "scenario_id": "markets.es.2026-001",
                    "task_type": "binary_probability",
                    "forecast": {
                        "target": "next_session_up",
                        "probability": 0.61,
                    },
                    "confidence": 0.72,
                }
            if name == "soccer_match_outcome_distribution.json":
                return {
                    "scenario_id": "sports.soccer.2026-003",
                    "task_type": "multiclass_distribution",
                    "forecast": {
                        "target": "match_result",
                        "class_probabilities": {
                            "home_win": 0.55,
                            "draw": 0.25,
                            "away_win": 0.20,
                        },
                    },
                }
            if name == "ff_sig317_20260407_cvd-divergence_long.json":
                return {
                    "scenario_id": "futures_flow.signal.317",
                    "task_type": "binary_probability",
                    "forecast": {
                        "target": "signal_correct",
                        "probability": 0.58,
                    },
                }
            if name == "pm_m516710_us-recession-in-2025.json":
                return {
                    "scenario_id": "polymarket_edge.market.516710",
                    "task_type": "binary_probability",
                    "forecast": {
                        "target": "market_resolves_yes",
                        "probability": 0.33,
                    },
                }
            return real_load_json(path)

        with mock.patch.object(reporting, "_find_submission_path", side_effect=fake_find_submission_path), \
             mock.patch.object(reporting, "_load_json", side_effect=fake_load_json):
            report = build_forecast_batch_report("virtual-submissions", split="all")

        self.assertGreaterEqual(report.total_tasks, 12)
        self.assertGreater(report.scored_tasks, 0)
        self.assertIn("markets_env", report.by_environment)
        self.assertIn("sports_env", report.by_environment)

        market_task = next(
            task for task in report.task_reports
            if task.env_name == "markets_env" and task.task_id == "es_next_session_probability"
        )
        self.assertIsNotNone(market_task.forecast_probability)
        self.assertIsNotNone(market_task.actual_outcome)

        non_empty_bins = [bucket for bucket in report.binary_calibration if bucket["count"]]
        self.assertTrue(non_empty_bins)
        self.assertIn("average_predicted", non_empty_bins[0])
        self.assertIn("observed_frequency", non_empty_bins[0])
        self.assertGreater(report.source_comparison["comparable_tasks"], 0)
        self.assertIsNotNone(report.source_comparison["average_source_score"])
        self.assertIsNotNone(report.source_comparison["average_model_edge"])

        futures_task = next(
            task for task in report.task_reports
            if task.env_name == "futures_flow_env" and task.task_id == "ff_sig317_20260407_cvd-divergence_long"
        )
        self.assertEqual(futures_task.source_label, "signal_confidence")
        self.assertIsNotNone(futures_task.source_score)
        self.assertIsNotNone(futures_task.source_edge)

    def test_text_report_includes_calibration_section(self) -> None:
        real_load_json = reporting._load_json

        def fake_load_json(path: Path):
            if Path(path).name == "es_next_session_probability.json":
                return {
                    "scenario_id": "markets.es.2026-001",
                    "task_type": "binary_probability",
                    "forecast": {
                        "target": "next_session_up",
                        "probability": 0.61,
                    },
                }
            if Path(path).name == "ff_sig317_20260407_cvd-divergence_long.json":
                return {
                    "scenario_id": "futures_flow.signal.317",
                    "task_type": "binary_probability",
                    "forecast": {
                        "target": "signal_correct",
                        "probability": 0.58,
                    },
                }
            return real_load_json(path)

        def fake_find_submission_path(_submission_root: Path, _env_name: str, task_id: str):
            if task_id == "ff_sig317_20260407_cvd-divergence_long":
                return Path("/virtual/ff_sig317_20260407_cvd-divergence_long.json")
            return None

        with mock.patch.object(reporting, "_find_submission_path", side_effect=fake_find_submission_path), \
             mock.patch.object(reporting, "_load_json", side_effect=fake_load_json):
            text = render_forecast_batch_report_text(
                build_forecast_batch_report("virtual-submissions", env_filter="futures_flow_env", split="all")
            )

        self.assertIn("Source priors:", text)
        self.assertIn("Binary calibration:", text)
        self.assertIn("futures_flow_env/ff_sig317_20260407_cvd-divergence_long", text)


if __name__ == "__main__":
    unittest.main()
