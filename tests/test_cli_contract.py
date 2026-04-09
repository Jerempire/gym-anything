from __future__ import annotations

import io
import sys
import types
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.modules.setdefault("fcntl", types.ModuleType("fcntl"))

from gym_anything import cli


class CliContractTests(unittest.TestCase):
    def test_short_environment_name_resolves_to_cua_world_environment(self) -> None:
        resolved = Path(cli._resolve_env_dir("moodle"))
        self.assertEqual(resolved, Path("benchmarks/cua_world/environments/moodle_env"))

    def test_interactive_run_accepts_short_environment_name(self) -> None:
        env = mock.Mock()
        reporter = mock.MagicMock()
        fake_progress = types.ModuleType("gym_anything.tui.progress")
        fake_progress.create_reporter = mock.Mock(return_value=reporter)
        fake_session_module = types.ModuleType("gym_anything.tui.session")
        fake_session_cls = mock.Mock()
        fake_session_module.InteractiveSession = fake_session_cls
        args = Namespace(
            env_dir="moodle",
            task=None,
            interactive=True,
            seed=42,
            open_vnc=False,
        )

        with mock.patch.object(cli, "_pick_random_task", return_value="demo_task"), \
             mock.patch.object(cli, "from_config", return_value=env) as mock_from_config, \
             mock.patch.dict(
                 sys.modules,
                 {
                     "gym_anything.tui.progress": fake_progress,
                     "gym_anything.tui.session": fake_session_module,
                 },
             ):
            result = cli.cmd_run(args)

        self.assertEqual(result, 0)
        self.assertEqual(
            Path(mock_from_config.call_args.args[0]),
            Path("benchmarks/cua_world/environments/moodle_env"),
        )
        self.assertEqual(mock_from_config.call_args.kwargs["task_id"], "demo_task")
        env.set_reporter.assert_called_once_with(reporter)
        env.reset.assert_called_once_with(seed=42)
        reporter.define_stages.assert_called_once()
        fake_session_cls.assert_called_once_with(env, auto_open_vnc=False)
        fake_session_cls.return_value.run.assert_called_once()

    def test_short_environment_name_resolves_to_forecasting_environment(self) -> None:
        resolved = Path(cli._resolve_env_dir("browser_research"))
        self.assertEqual(
            resolved,
            Path("benchmarks/forecasting_world/environments/browser_research_env"),
        )

    def test_forecast_report_command_scores_submission_directory(self) -> None:
        fake_report = mock.Mock()
        fake_report.to_dict.return_value = {"average_score": 91.0}

        with mock.patch(
            "benchmarks.forecasting_world.evaluation.build_forecast_batch_report",
            return_value=fake_report,
        ) as mock_build, mock.patch(
            "benchmarks.forecasting_world.evaluation.render_forecast_batch_report_text",
            return_value="Submission root: fake\n[markets_env] avg=91.00\n[OK] markets_env/es_next_session_probability score=91.00",
        ):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                result = cli.main(
                    [
                        "forecast-report",
                        "fake-submissions",
                        "--env",
                        "markets_env",
                    ]
                )

        self.assertEqual(result, 0)
        mock_build.assert_called_once_with(
            "fake-submissions",
            env_filter="markets_env",
            split="all",
        )
        output = buffer.getvalue()
        self.assertIn("Submission root:", output)
        self.assertIn("[markets_env]", output)
        self.assertIn("es_next_session_probability", output)

    def test_benchmark_batch_uses_forecasting_test_split(self) -> None:
        args = Namespace(
            env_dir="markets_env",
            split="test",
            surface="raw",
            agent="MockAgent",
            seed=42,
            cache_level="pre_start",
            steps=None,
            model=None,
            exp_name=None,
            use_cache=False,
            use_savevm=False,
            temperature=None,
            agent_arg=None,
        )

        with mock.patch.object(cli.subprocess, "run", return_value=Namespace(returncode=0)) as mock_run:
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                result = cli._run_benchmark_batch(args)

        self.assertEqual(result, 0)
        mock_run.assert_called_once()
        cmd = mock_run.call_args.args[0]
        self.assertEqual(cmd[0], sys.executable)
        self.assertEqual(cmd[1:4], ["-m", "gym_anything.cli", "benchmark"])
        self.assertEqual(Path(cmd[4]), Path("benchmarks/forecasting_world/environments/markets_env"))
        self.assertEqual(cmd[5:10], ["--task", "trade_or_abstain", "--agent", "MockAgent", "--seed"])
        self.assertIn("Running 1 tasks with MockAgent", buffer.getvalue())
        self.assertIn("markets_env / trade_or_abstain", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
