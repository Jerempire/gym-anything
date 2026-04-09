from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENV_NAME = "futures_walk_forward_env"
TARGET_NAME = "positive_oos_sharpe"
DEFAULT_JSON_PATH = Path.home() / "Projects" / "finance" / "futures-flow" / "data" / "walk_forward_results.json"
WORKSPACE_ROOT = "/home/ga/Desktop/FuturesWalkForwardTasks"
FORECAST_ROOT = "/home/ga/Documents/FuturesWalkForwardForecasts"
LOCAL_PORT = 8127
PREFERRED_STRATEGIES = [
    "liq_sweep",
    "order_block",
    "breaker",
    "fvg",
    "judas_swing",
    "silver_bullet",
    "vwap_flip",
    "atr_breakout",
    "ict_entry",
]


def slugify(text: str, *, max_len: int = 48) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not normalized:
        normalized = "strategy"
    return normalized[:max_len].rstrip("-")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


@dataclass
class ImportedWalkForwardTask:
    strategy: str
    filter_name: str
    total_folds: int
    fold_number: int
    train_range: str
    test_range: str
    in_sample_sharpe: float
    best_params: dict[str, Any]
    selected_oos_sharpe: float
    selected_oos_trades: int
    selected_oos_wr: float
    selected_oos_pnl: float
    prior_positive_rate: float
    prior_avg_oos_sharpe: float
    prior_avg_oos_wr: float
    prior_avg_oos_pnl: float
    prior_avg_oos_trades: float
    prior_folds: list[dict[str, Any]]

    @property
    def task_id(self) -> str:
        return f"ffwf_{slugify(self.strategy, max_len=24)}_fold{self.fold_number}"

    @property
    def scenario_id(self) -> str:
        return f"futures_flow.walk_forward.{slugify(self.strategy, max_len=24)}.fold{self.fold_number}"


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def load_importable_tasks(json_path: Path, *, limit: int) -> list[ImportedWalkForwardTask]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    imported: list[ImportedWalkForwardTask] = []
    used: set[str] = set()

    for strategy_name in PREFERRED_STRATEGIES + sorted(data):
        if strategy_name in used or strategy_name not in data:
            continue
        payload = data[strategy_name]
        folds = [fold for fold in payload.get("folds", []) if fold.get("oos_trades", 0) > 0]
        if len(folds) < 2:
            continue

        selected = folds[-1]
        prior = [fold for fold in folds if fold["fold"] < selected["fold"]]
        if not prior:
            continue

        prior_sharpes = [float(fold.get("oos_sharpe", 0.0)) for fold in prior]
        prior_wrs = [float(fold.get("oos_wr", 0.0)) for fold in prior]
        prior_pnls = [float(fold.get("oos_pnl", 0.0)) for fold in prior]
        prior_trades = [int(fold.get("oos_trades", 0)) for fold in prior]
        imported.append(
            ImportedWalkForwardTask(
                strategy=str(payload.get("strategy") or strategy_name),
                filter_name=str(payload.get("filter") or "none"),
                total_folds=int(payload.get("total_folds") or len(payload.get("folds", []))),
                fold_number=int(selected["fold"]),
                train_range=str(selected["train"]),
                test_range=str(selected["test"]),
                in_sample_sharpe=float(selected.get("is_sharpe", 0.0)),
                best_params=dict(selected.get("is_best_params") or {}),
                selected_oos_sharpe=float(selected.get("oos_sharpe", 0.0)),
                selected_oos_trades=int(selected.get("oos_trades", 0)),
                selected_oos_wr=float(selected.get("oos_wr", 0.0)),
                selected_oos_pnl=float(selected.get("oos_pnl", 0.0)),
                prior_positive_rate=sum(1 for value in prior_sharpes if value > 0.0) / len(prior_sharpes),
                prior_avg_oos_sharpe=_mean(prior_sharpes),
                prior_avg_oos_wr=_mean(prior_wrs),
                prior_avg_oos_pnl=_mean(prior_pnls),
                prior_avg_oos_trades=_mean([float(value) for value in prior_trades]),
                prior_folds=[
                    {
                        "fold": int(fold["fold"]),
                        "train": str(fold["train"]),
                        "test": str(fold["test"]),
                        "oos_sharpe": float(fold.get("oos_sharpe", 0.0)),
                        "oos_trades": int(fold.get("oos_trades", 0)),
                        "oos_wr": float(fold.get("oos_wr", 0.0)),
                        "oos_pnl": float(fold.get("oos_pnl", 0.0)),
                    }
                    for fold in prior[-6:]
                ],
            )
        )
        used.add(strategy_name)
        if len(imported) >= limit:
            break

    return imported


def render_dossier_html(task: ImportedWalkForwardTask) -> str:
    params_json = json.dumps(task.best_params, indent=2, ensure_ascii=False)
    prior_rows = "".join(
        (
            "<tr>"
            f"<td>{fold['fold']}</td>"
            f"<td>{escape(fold['test'])}</td>"
            f"<td>{fold['oos_trades']}</td>"
            f"<td>{fold['oos_wr']:.3f}</td>"
            f"<td>{fold['oos_sharpe']:.2f}</td>"
            f"<td>{fold['oos_pnl']:+.2f}</td>"
            "</tr>"
        )
        for fold in task.prior_folds
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>{escape(task.task_id)}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 2rem auto; max-width: 1080px; color: #1f2937; line-height: 1.5; }}
      .card {{ border: 1px solid #d1d5db; border-radius: 10px; padding: 1rem 1.25rem; background: #f9fafb; margin-bottom: 1rem; }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 0.75rem; }}
      th, td {{ border: 1px solid #d1d5db; padding: 0.45rem 0.6rem; text-align: left; }}
      th {{ background: #eef2ff; }}
      pre {{ background: #111827; color: #f9fafb; padding: 0.9rem; border-radius: 8px; overflow-x: auto; }}
      code {{ background: #eef2ff; padding: 0.1rem 0.3rem; border-radius: 4px; }}
    </style>
  </head>
  <body>
    <h1>{escape(task.strategy)} walk-forward replay</h1>
    <div class="card">
      <p>Forecast whether this strategy's selected out-of-sample fold will finish with positive OOS Sharpe. The hidden label is based on the imported fold result from <code>futures-flow</code>.</p>
      <p><strong>Selected fold:</strong> {task.fold_number} of {task.total_folds}</p>
      <p><strong>Train window:</strong> {escape(task.train_range)}</p>
      <p><strong>Test window:</strong> {escape(task.test_range)}</p>
      <p><strong>Filter family:</strong> {escape(task.filter_name)}</p>
      <p><strong>In-sample Sharpe:</strong> {task.in_sample_sharpe:.2f}</p>
      <p><strong>Prior positive-fold rate:</strong> {task.prior_positive_rate:.3f}</p>
      <p><strong>Prior avg OOS Sharpe:</strong> {task.prior_avg_oos_sharpe:.2f}</p>
      <p><strong>Prior avg OOS WR:</strong> {task.prior_avg_oos_wr:.3f}</p>
      <p><strong>Prior avg OOS P&L:</strong> {task.prior_avg_oos_pnl:+.2f}</p>
      <p><strong>Prior avg OOS trades:</strong> {task.prior_avg_oos_trades:.1f}</p>
    </div>
    <div class="card">
      <h2>Best In-Sample Params For Selected Fold</h2>
      <pre>{escape(params_json)}</pre>
    </div>
    <div class="card">
      <h2>Recent Prior Fold History</h2>
      <table>
        <thead>
          <tr>
            <th>Fold</th>
            <th>Test window</th>
            <th>Trades</th>
            <th>WR</th>
            <th>OOS Sharpe</th>
            <th>OOS P&amp;L</th>
          </tr>
        </thead>
        <tbody>
          {prior_rows}
        </tbody>
      </table>
    </div>
    <div class="card">
      <p>Submit a <code>binary_probability</code> forecast for target <code>{TARGET_NAME}</code>.</p>
    </div>
  </body>
</html>
"""


def render_scenario_json(task: ImportedWalkForwardTask) -> dict[str, Any]:
    return {
        "source_project": "futures-flow",
        "scenario_id": task.scenario_id,
        "strategy": task.strategy,
        "filter_name": task.filter_name,
        "fold_number": task.fold_number,
        "total_folds": task.total_folds,
        "train_range": task.train_range,
        "test_range": task.test_range,
        "in_sample_sharpe": task.in_sample_sharpe,
        "best_params": task.best_params,
        "prior_positive_rate": task.prior_positive_rate,
        "prior_avg_oos_sharpe": task.prior_avg_oos_sharpe,
        "prior_avg_oos_wr": task.prior_avg_oos_wr,
        "prior_avg_oos_pnl": task.prior_avg_oos_pnl,
        "prior_avg_oos_trades": task.prior_avg_oos_trades,
        "prior_folds": task.prior_folds,
    }


def build_env_files(env_dir: Path) -> None:
    scripts_dir = env_dir / "scripts"
    tasks_dir = env_dir / "tasks"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir.mkdir(parents=True, exist_ok=True)

    write_json(
        env_dir / "env.json",
        {
            "id": "futures_walk_forward_env@0.1",
            "version": "0.1",
            "base": "ubuntu-gnome-systemd_highres",
            "description": "Replay environment generated from futures-flow walk-forward fold results.",
            "category": ["forecasting", "research", "browser", "desktop", "finance"],
            "tags": ["forecasting", "futures", "walk-forward", "strategy-selection", "browser"],
            "resources": {"cpu": 2, "mem_gb": 4, "gpu": 0, "net": False},
            "observation": [{"type": "rgb_screen", "fps": 10, "resolution": [1920, 1080], "inline": False}],
            "action": [{"type": "mouse"}, {"type": "keyboard"}],
            "synchronous": True,
            "step_cycle_ms": 200,
            "recording": {
                "enable": True,
                "output_dir": "benchmarks/forecasting_world/environments/futures_walk_forward_env/artifacts",
            },
            "vnc": {"enable": True, "host_port": 5972, "password": "password"},
            "security": {
                "user": "root",
                "cap_drop": ["ALL"],
                "privileged": True,
                "use_systemd": True,
                "mount_cgroups": True,
                "cgroupns_host": True,
                "tmpfs_run": True,
                "runtime": "sysbox-runc",
            },
            "mounts": [
                {
                    "source": "benchmarks/forecasting_world/environments/futures_walk_forward_env/scripts",
                    "target": "/workspace/scripts",
                    "mode": "ro",
                },
                {
                    "source": "benchmarks/forecasting_world/environments/futures_walk_forward_env/tasks",
                    "target": "/workspace/tasks",
                    "mode": "ro",
                },
            ],
            "hooks": {
                "pre_start": "/workspace/scripts/install_futures_walk_forward_env.sh",
                "post_start": "/workspace/scripts/setup_futures_walk_forward_env.sh",
            },
            "user_accounts": [
                {
                    "name": "ga",
                    "password": "password123",
                    "role": "researcher",
                    "permissions": {
                        "sudo": True,
                        "sudo_nopasswd": True,
                        "groups": ["sudo", "audio", "video", "input"],
                        "shell": "/bin/bash",
                        "env_vars": {"DISPLAY": ":1"},
                    },
                }
            ],
        },
    )
    write_text(
        scripts_dir / "install_futures_walk_forward_env.sh",
        f"""#!/bin/bash
set -euo pipefail

mkdir -p {WORKSPACE_ROOT}
mkdir -p {FORECAST_ROOT}
mkdir -p /tmp/{ENV_NAME}
chown -R ga:ga {WORKSPACE_ROOT} {FORECAST_ROOT} /tmp/{ENV_NAME}
""",
    )
    write_text(
        scripts_dir / "serve_research_workspace.py",
        (ROOT / "environments" / "browser_research_env" / "scripts" / "serve_research_workspace.py").read_text(encoding="utf-8"),
    )
    write_text(
        scripts_dir / "setup_futures_walk_forward_env.sh",
        f"""#!/bin/bash
set -euo pipefail

mkdir -p {WORKSPACE_ROOT}
mkdir -p {FORECAST_ROOT}
mkdir -p /tmp/{ENV_NAME}
rm -f /tmp/task_result.json /tmp/exported_forecast.json

cat > {WORKSPACE_ROOT}/index.html <<'EOF'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Futures Walk-Forward Workspace</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 2rem auto; max-width: 900px; line-height: 1.5; color: #1f2937; }}
      .card {{ border: 1px solid #d1d5db; border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 1rem; background: #f9fafb; }}
      code {{ background: #eef2ff; padding: 0.1rem 0.3rem; border-radius: 4px; }}
    </style>
  </head>
  <body>
    <h1>Futures Walk-Forward Workspace</h1>
    <div class="card">
      <p>This environment replays futures strategy walk-forward folds imported from <code>futures-flow</code>.</p>
      <p>After a task reset, open its page at <code>http://127.0.0.1:{LOCAL_PORT}/&lt;task_id&gt;/</code>.</p>
      <p>Forecast outputs belong under <code>{FORECAST_ROOT}/</code>.</p>
    </div>
  </body>
</html>
EOF

cat > /home/ga/Desktop/open_futures_walk_forward_workspace.sh <<'EOF'
#!/bin/bash
set -euo pipefail
xdg-open "http://127.0.0.1:{LOCAL_PORT}/"
EOF
chmod +x /home/ga/Desktop/open_futures_walk_forward_workspace.sh

cat > /home/ga/Desktop/Futures\\ Walk\\ Forward\\ Workspace.desktop <<'EOF'
[Desktop Entry]
Type=Application
Version=1.0
Name=Futures Walk Forward Workspace
Comment=Open the local futures walk-forward workspace
Exec=/home/ga/Desktop/open_futures_walk_forward_workspace.sh
Terminal=false
Categories=Education;Science;
EOF
chmod +x /home/ga/Desktop/Futures\\ Walk\\ Forward\\ Workspace.desktop

if [ -f /tmp/{ENV_NAME}/research_server.pid ]; then
  old_pid="$(cat /tmp/{ENV_NAME}/research_server.pid || true)"
  if [ -n "${{old_pid}}" ] && kill -0 "${{old_pid}}" 2>/dev/null; then
    kill "${{old_pid}}" || true
  fi
fi

sudo -u ga bash -lc 'cd {WORKSPACE_ROOT} && nohup python3 /workspace/scripts/serve_research_workspace.py --root {WORKSPACE_ROOT} --port {LOCAL_PORT} >/tmp/{ENV_NAME}/research_server.log 2>&1 & echo $! >/tmp/{ENV_NAME}/research_server.pid'

chown -R ga:ga {WORKSPACE_ROOT} {FORECAST_ROOT} /tmp/{ENV_NAME}
chown ga:ga /home/ga/Desktop/open_futures_walk_forward_workspace.sh /home/ga/Desktop/Futures\\ Walk\\ Forward\\ Workspace.desktop
""",
    )


def render_setup_script(task: ImportedWalkForwardTask) -> str:
    return f"""#!/bin/bash
set -euo pipefail

TASK_ID="{task.task_id}"
TASK_ROOT="{WORKSPACE_ROOT}/${{TASK_ID}}"
FORECAST_PATH="{FORECAST_ROOT}/${{TASK_ID}}_forecast.json"
mkdir -p "$TASK_ROOT" "{FORECAST_ROOT}"
cp "/workspace/tasks/${{TASK_ID}}/scenario.json" "${{TASK_ROOT}}/scenario.json"
cp "/workspace/tasks/${{TASK_ID}}/dossier.html" "${{TASK_ROOT}}/dossier.html"
cat > "${{TASK_ROOT}}/README.txt" <<EOF
Review dossier.html and scenario.json, then save your forecast to:
${{FORECAST_PATH}}

Browser workspace:
http://127.0.0.1:{LOCAL_PORT}/${{TASK_ID}}/

Expected schema:
{{
  "scenario_id": "{task.scenario_id}",
  "task_type": "binary_probability",
  "forecast": {{
    "target": "{TARGET_NAME}",
    "probability": 0.50
  }},
  "confidence": 0.50,
  "notes": "Short rationale"
}}
EOF
cat > "${{TASK_ROOT}}/index.html" <<EOF
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>${{TASK_ID}}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 2rem auto; max-width: 960px; color: #1f2937; }}
      .card {{ border: 1px solid #d1d5db; border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 1rem; background: #f9fafb; }}
      code {{ background: #eef2ff; padding: 0.1rem 0.3rem; border-radius: 4px; }}
      a {{ color: #1d4ed8; }}
    </style>
  </head>
  <body>
    <h1>${{TASK_ID}}</h1>
    <div class="card">
      <p>Forecast target: <code>{TARGET_NAME}</code></p>
      <p>Forecast output path: <code>${{FORECAST_PATH}}</code></p>
    </div>
    <div class="card">
      <h2>Evidence</h2>
      <ul>
        <li><a href="./dossier.html">Imported walk-forward dossier</a></li>
        <li><a href="./scenario.json">Scenario metadata</a></li>
        <li><a href="./README.txt">Task instructions</a></li>
      </ul>
    </div>
  </body>
</html>
EOF
rm -f "$FORECAST_PATH" /tmp/task_result.json /tmp/exported_forecast.json
date +%s > /tmp/${{TASK_ID}}_start.txt
chown -R ga:ga "$TASK_ROOT" "{FORECAST_ROOT}"
"""


EXPORT_SCRIPT_TEMPLATE = """#!/bin/bash
set -euo pipefail

TASK_ID="{task_id}"
FORECAST_PATH="{forecast_root}/${{TASK_ID}}_forecast.json"
START_TS=$(cat /tmp/${{TASK_ID}}_start.txt 2>/dev/null || echo "0")
FORECAST_EXISTS=false
FORECAST_SIZE=0
FORECAST_CREATED_AFTER_START=false

if [ -f "$FORECAST_PATH" ]; then
    FORECAST_EXISTS=true
    FORECAST_SIZE=$(stat -c %s "$FORECAST_PATH")
    FORECAST_MTIME=$(stat -c %Y "$FORECAST_PATH")
    if [ "$FORECAST_MTIME" -ge "$START_TS" ]; then
        FORECAST_CREATED_AFTER_START=true
    fi
    cp "$FORECAST_PATH" /tmp/exported_forecast.json
fi

cat > /tmp/task_result.json <<EOF
{{
  "forecast_exists": $FORECAST_EXISTS,
  "forecast_size": $FORECAST_SIZE,
  "forecast_created_after_start": $FORECAST_CREATED_AFTER_START,
  "forecast_path": "/tmp/exported_forecast.json"
}}
EOF
chmod 644 /tmp/task_result.json 2>/dev/null || true
chmod 644 /tmp/exported_forecast.json 2>/dev/null || true
"""


VERIFIER_TEMPLATE = """#!/usr/bin/env python3
from __future__ import annotations

from benchmarks.forecasting_world.shared import (
    SchemaValidationError,
    build_feedback,
    combine_weighted_scores,
    load_exported_forecast,
    load_exported_result,
    load_hidden_outcome,
    probability_score,
    validate_submission,
)


def verify_imported_futures_walk_forward_task(traj, env_info, task_info):
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
        )
    except SchemaValidationError as exc:
        return {"passed": False, "score": 0, "feedback": f"Schema validation failed: {exc}"}
    except Exception as exc:
        return {"passed": False, "score": 0, "feedback": f"Failed to load forecast: {exc}"}

    if normalized["scenario_id"] != metadata["scenario_id"]:
        return {"passed": False, "score": 0, "feedback": "Scenario id does not match task metadata"}

    outcome = load_hidden_outcome(__file__, metadata["outcome_ref"])
    forecast_probability = normalized["forecast"]["probability"]
    outcome_value = int(outcome["outcome"])
    quality_score = probability_score(forecast_probability, outcome_value)
    completion_score = 100.0 if result.get("forecast_size", 0) > 0 else 0.0
    final_score = combine_weighted_scores([(quality_score, 0.85), (completion_score, 0.15)])

    feedback.append(f"Probability={forecast_probability:.3f}")
    feedback.append(f"Outcome={outcome_value}")
    feedback.append(f"Forecast quality={quality_score:.1f}")
    feedback.append(f"Hidden OOS Sharpe={float(outcome['oos_sharpe']):.2f}")
    return {
        "passed": final_score >= metadata.get("pass_threshold", 65),
        "score": round(final_score),
        "feedback": build_feedback(feedback),
    }
"""


def build_task_files(env_dir: Path, datasets_dir: Path, task: ImportedWalkForwardTask) -> None:
    task_dir = env_dir / "tasks" / task.task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        task_dir / "task.json",
        {
            "id": f"{task.task_id}@1",
            "version": "1.0",
            "env_id": "futures_walk_forward_env@0.1",
            "description": (
                f"You are replaying a futures-flow walk-forward fold. Review the task workspace at "
                f"http://127.0.0.1:{LOCAL_PORT}/{task.task_id}/ or the mirrored files under "
                f"{WORKSPACE_ROOT}/{task.task_id}/, then save a forecast to "
                f"{FORECAST_ROOT}/{task.task_id}_forecast.json. "
                f"Assign a probability to the binary target '{TARGET_NAME}'."
            ),
            "difficulty": "medium",
            "init": {"timeout_sec": 300, "max_steps": 45, "reward_type": "sparse"},
            "hooks": {
                "pre_task": f"/workspace/tasks/{task.task_id}/setup_task.sh",
                "post_task": f"/workspace/tasks/{task.task_id}/export_result.sh",
            },
            "metadata": {
                "scenario_id": task.scenario_id,
                "forecast_path": f"{FORECAST_ROOT}/{task.task_id}_forecast.json",
                "expected_task_type": "binary_probability",
                "expected_target": TARGET_NAME,
                "outcome_ref": f"futures_walk_forward/{task.task_id}.hidden.json",
                "pass_threshold": 65,
            },
            "success": {"mode": "program", "spec": {"program": "verifier.py::verify_imported_futures_walk_forward_task"}},
        },
    )
    write_json(task_dir / "scenario.json", render_scenario_json(task))
    write_text(task_dir / "dossier.html", render_dossier_html(task))
    write_text(task_dir / "setup_task.sh", render_setup_script(task))
    write_text(
        task_dir / "export_result.sh",
        EXPORT_SCRIPT_TEMPLATE.format(task_id=task.task_id, forecast_root=FORECAST_ROOT),
    )
    write_text(task_dir / "verifier.py", VERIFIER_TEMPLATE)

    write_json(
        datasets_dir / f"{task.task_id}.hidden.json",
        {
            "scenario_id": task.scenario_id,
            "source_project": "futures-flow",
            "strategy": task.strategy,
            "fold_number": task.fold_number,
            "outcome": int(task.selected_oos_sharpe > 0.0),
            "oos_sharpe": task.selected_oos_sharpe,
            "oos_trades": task.selected_oos_trades,
            "oos_wr": task.selected_oos_wr,
            "oos_pnl": task.selected_oos_pnl,
        },
    )


def write_split_file(split_dir: Path, task_ids: list[str]) -> None:
    split_dir.mkdir(parents=True, exist_ok=True)
    if not task_ids:
        train_tasks: list[str] = []
        test_tasks: list[str] = []
    else:
        train_count = max(1, int(round(len(task_ids) * 0.67)))
        if train_count >= len(task_ids) and len(task_ids) > 1:
            train_count = len(task_ids) - 1
        train_tasks = task_ids[:train_count]
        test_tasks = task_ids[train_count:] or task_ids[-1:]
        if not train_tasks:
            train_tasks = task_ids[:-1] or task_ids
    write_json(
        split_dir / f"{ENV_NAME}_split.json",
        {
            "env_folder": f"benchmarks/forecasting_world/environments/{ENV_NAME}",
            "train_ratio": 0.67,
            "train_tasks": train_tasks,
            "test_tasks": test_tasks,
        },
    )


def write_seed_manifest(env_dir: Path, tasks: list[ImportedWalkForwardTask]) -> None:
    payload = [
        {
            "task_id": task.task_id,
            "strategy": task.strategy,
            "fold_number": task.fold_number,
            "test_range": task.test_range,
        }
        for task in tasks
    ]
    write_json(env_dir / "tasks" / "seed_tasks.json", payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import futures-flow walk-forward folds into forecasting_world.")
    parser.add_argument("--json-path", type=Path, default=DEFAULT_JSON_PATH)
    parser.add_argument("--limit", type=int, default=6)
    args = parser.parse_args()

    tasks = load_importable_tasks(args.json_path, limit=args.limit)
    env_dir = ROOT / "environments" / ENV_NAME
    datasets_dir = ROOT / "datasets" / "futures_walk_forward"
    if env_dir.exists():
        shutil.rmtree(env_dir)
    if datasets_dir.exists():
        shutil.rmtree(datasets_dir)
    build_env_files(env_dir)
    datasets_dir.mkdir(parents=True, exist_ok=True)
    task_ids: list[str] = []
    for task in tasks:
        build_task_files(env_dir, datasets_dir, task)
        task_ids.append(task.task_id)

    write_seed_manifest(env_dir, tasks)
    write_split_file(ROOT / "splits", task_ids)

    print(f"Imported {len(task_ids)} futures walk-forward tasks into {env_dir}")
    for task in tasks:
        print(f"- {task.task_id}: {task.strategy} fold {task.fold_number} ({task.test_range})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
