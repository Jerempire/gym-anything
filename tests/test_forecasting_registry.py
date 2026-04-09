from __future__ import annotations

import unittest

from benchmarks.forecasting_world.registry import get_tasks_for_environment, load_environment_task_splits


class ForecastingRegistryTests(unittest.TestCase):
    def test_markets_env_tasks_are_discoverable(self) -> None:
        tasks = get_tasks_for_environment("markets_env")
        self.assertIn("es_next_session_probability", tasks)
        self.assertIn("nq_volatility_regime", tasks)
        self.assertIn("trade_or_abstain", tasks)

    def test_sports_env_tasks_are_discoverable(self) -> None:
        tasks = get_tasks_for_environment("sports_env")
        self.assertIn("nba_moneyline_probability", tasks)
        self.assertIn("nfl_total_direction", tasks)
        self.assertIn("soccer_match_outcome_distribution", tasks)

    def test_psychology_env_tasks_are_discoverable(self) -> None:
        tasks = get_tasks_for_environment("psychology_env")
        self.assertIn("message_compliance_likelihood", tasks)
        self.assertIn("burnout_risk_bucket", tasks)
        self.assertIn("trust_repair_outcome", tasks)

    def test_browser_research_env_tasks_are_discoverable(self) -> None:
        tasks = get_tasks_for_environment("browser_research_env")
        self.assertIn("event_probability_from_dossier", tasks)
        self.assertIn("linked_market_edge_decision", tasks)
        self.assertIn("forecast_revision_after_new_report", tasks)

    def test_forecast_hub_env_tasks_are_discoverable(self) -> None:
        tasks = get_tasks_for_environment("forecast_hub_env")
        self.assertIn("fh_q23_will-donald-trump-and-xi-jinping-meet-in-person", tasks)
        self.assertIn("fh_q51_will-iowa-win-the-2026-ncaa-tournament", tasks)
        self.assertIn("fh_q50_will-elon-musk-post-1400-tweets-in-march-2026", tasks)

    def test_polymarket_edge_env_tasks_are_discoverable(self) -> None:
        tasks = get_tasks_for_environment("polymarket_edge_env")
        self.assertIn("pm_m517428_will-israel-annex-syrian-territory-before-ju", tasks)
        self.assertIn("pm_m539203_will-peoples-action-party-pap-win-the-2025-s", tasks)
        self.assertIn("pm_m516710_us-recession-in-2025", tasks)

    def test_futures_flow_env_tasks_are_discoverable(self) -> None:
        tasks = get_tasks_for_environment("futures_flow_env")
        self.assertIn("ff_sig367_20260408_liq-sweep_short", tasks)
        self.assertIn("ff_sig317_20260407_cvd-divergence_long", tasks)
        self.assertIn("ff_sig353_20260407_timesfm_short", tasks)

    def test_futures_walk_forward_env_tasks_are_discoverable(self) -> None:
        tasks = get_tasks_for_environment("futures_walk_forward_env")
        self.assertIn("ffwf_liq-sweep_fold26", tasks)
        self.assertIn("ffwf_judas-swing_fold26", tasks)
        self.assertIn("ffwf_silver-bullet_fold26", tasks)

    def test_default_test_split_is_non_empty_for_all_forecasting_environments(self) -> None:
        registry = load_environment_task_splits()
        for env_name in (
            "markets_env",
            "sports_env",
            "psychology_env",
            "browser_research_env",
            "forecast_hub_env",
            "polymarket_edge_env",
            "futures_flow_env",
            "futures_walk_forward_env",
        ):
            self.assertIn(env_name, registry)
            self.assertTrue(
                registry[env_name]["test"],
                f"{env_name} should expose at least one test task",
            )

    def test_named_test_tasks_match_split_files(self) -> None:
        self.assertEqual(get_tasks_for_environment("markets_env", split="test"), ["trade_or_abstain"])
        self.assertEqual(
            get_tasks_for_environment("sports_env", split="test"),
            ["soccer_match_outcome_distribution"],
        )
        self.assertEqual(
            get_tasks_for_environment("psychology_env", split="test"),
            ["trust_repair_outcome"],
        )
        self.assertEqual(
            get_tasks_for_environment("browser_research_env", split="test"),
            ["forecast_revision_after_new_report"],
        )
        self.assertEqual(
            get_tasks_for_environment("forecast_hub_env", split="test"),
            [
                "fh_q39_will-russia-capture-kostyantynivka-by-april-30",
                "fh_q50_will-elon-musk-post-1400-tweets-in-march-2026",
            ],
        )
        self.assertEqual(
            get_tasks_for_environment("polymarket_edge_env", split="test"),
            [
                "pm_m535383_will-iphone-17-cost-1500-or-more",
                "pm_m535384_will-iphone-17-cost-2000-or-more",
                "pm_m525882_will-the-edmonton-oilers-win-the-western-con",
            ],
        )
        self.assertEqual(
            get_tasks_for_environment("futures_flow_env", split="test"),
            [
                "ff_sig317_20260407_cvd-divergence_long",
                "ff_sig321_20260407_timesfm_long",
                "ff_sig353_20260407_timesfm_short",
            ],
        )
        self.assertEqual(
            get_tasks_for_environment("futures_walk_forward_env", split="test"),
            [
                "ffwf_judas-swing_fold26",
                "ffwf_silver-bullet_fold26",
            ],
        )


if __name__ == "__main__":
    unittest.main()
