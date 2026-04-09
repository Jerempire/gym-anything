from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENV_NAME = "futures_flow_env"
TARGET_NAME = "signal_correct"
DEFAULT_DB_PATH = Path.home() / "Projects" / "finance" / "futures-flow" / "data" / "daily_signals.db"
DEFAULT_REPORTS_DIR = Path.home() / "Projects" / "finance" / "futures-flow" / "data" / "reports"
WORKSPACE_ROOT = "/home/ga/Desktop/FuturesFlowTasks"
FORECAST_ROOT = "/home/ga/Documents/FuturesFlowForecasts"
LOCAL_PORT = 8126


@dataclass
class ImportedSignal:
    signal_id: int
    signal_date: str
    signal_time: str
    direction: str
    strategy: str
    entry_price: float
    confidence: float
    ofi_value: float | None
    cvd_value: float | None
    atr_value: float | None
    hold_bars: int
    target_price: float | None
    resolved_at: str
    outcome: float
    outcome_price: float | None
    outcome_return: float | None
    params_source: str | None
    macro_regime: str | None

    @property
    def task_id(self) -> str:
        date_token = self.signal_date.replace("-", "")
        direction = self.direction.lower()
        strategy = slugify(self.strategy, max_len=20)
        return f"ff_sig{self.signal_id}_{date_token}_{strategy}_{direction}"

    @property
    def scenario_id(self) -> str:
        return f"futures_flow.signal.{self.signal_id}"


def slugify(text: str, *, max_len: int = 48) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not normalized:
        normalized = "signal"
    return normalized[:max_len].rstrip("-")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def connect_readonly(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_importable_signals(db_path: Path, *, limit: int) -> list[ImportedSignal]:
    conn = connect_readonly(db_path)
    try:
        rows = conn.execute(
            """
            SELECT *
            FROM signals
            WHERE outcome_correct IN (0, 1)
              AND outcome_price IS NOT NULL
              AND resolved_at IS NOT NULL
            ORDER BY signal_date DESC, confidence DESC, id DESC
            """
        ).fetchall()

        imported: list[ImportedSignal] = []
        seen_keys: set[tuple[str, str, str]] = set()
        for row in rows:
            signal_date = str(row["signal_date"])
            strategy = str(row["strategy"] or "signal")
            direction = str(row["direction"])
            dedupe_key = (signal_date, strategy, direction)
            if dedupe_key in seen_keys:
                continue
            imported.append(
                ImportedSignal(
                    signal_id=int(row["id"]),
                    signal_date=signal_date,
                    signal_time=str(row["signal_time"]),
                    direction=direction,
                    strategy=strategy,
                    entry_price=float(row["entry_price"]),
                    confidence=float(row["confidence"]),
                    ofi_value=float(row["ofi_value"]) if row["ofi_value"] is not None else None,
                    cvd_value=float(row["cvd_value"]) if row["cvd_value"] is not None else None,
                    atr_value=float(row["atr_value"]) if row["atr_value"] is not None else None,
                    hold_bars=int(row["hold_bars"]),
                    target_price=float(row["target_price"]) if row["target_price"] is not None else None,
                    resolved_at=str(row["resolved_at"]),
                    outcome=float(row["outcome_correct"]),
                    outcome_price=float(row["outcome_price"]) if row["outcome_price"] is not None else None,
                    outcome_return=float(row["outcome_return"]) if row["outcome_return"] is not None else None,
                    params_source=row["params_source"],
                    macro_regime=row["macro_regime"],
                )
            )
            seen_keys.add(dedupe_key)
            if len(imported) >= limit:
                break
        return imported
    finally:
        conn.close()


def render_dossier_html(signal: ImportedSignal, *, has_daily_report: bool) -> str:
    report_note = (
        "<p>A same-day ES signal report is available as <code>report.html</code> in this task workspace.</p>"
        if has_daily_report
        else "<p>No archived same-day HTML signal report was available for this signal date.</p>"
    )

    def metric(label: str, value: str) -> str:
        return f"<li><strong>{escape(label)}:</strong> {escape(value)}</li>"

    metrics = [
        metric("Signal date", signal.signal_date),
        metric("Signal time", signal.signal_time),
        metric("Direction", signal.direction),
        metric("Strategy", signal.strategy),
        metric("Entry price", f"{signal.entry_price:.2f}"),
        metric("Hold bars", str(signal.hold_bars)),
        metric("Confidence", f"{signal.confidence:.3f}"),
        metric("Parameter source", str(signal.params_source or "unknown")),
        metric("Macro regime", str(signal.macro_regime or "unknown")),
    ]
    if signal.target_price is not None:
        metrics.append(metric("Target price", f"{signal.target_price:.2f}"))
    if signal.atr_value is not None:
        metrics.append(metric("ATR", f"{signal.atr_value:.2f}"))
    if signal.ofi_value is not None:
        metrics.append(metric("OFI", f"{signal.ofi_value:.4f}"))
    if signal.cvd_value is not None:
        metrics.append(metric("CVD", f"{signal.cvd_value:.4f}"))

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>{escape(signal.task_id)}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 2rem auto; max-width: 980px; color: #1f2937; line-height: 1.5; }}
      .card {{ border: 1px solid #d1d5db; border-radius: 10px; padding: 1rem 1.25rem; background: #f9fafb; margin-bottom: 1rem; }}
      ul {{ padding-left: 1.2rem; }}
      code {{ background: #eef2ff; padding: 0.1rem 0.3rem; border-radius: 4px; }}
    </style>
  </head>
  <body>
    <h1>{escape(signal.strategy)} signal replay</h1>
    <div class="card">
      <p>This task replays a resolved intraday futures signal imported from <code>futures-flow</code>. Assign your own probability that the directional signal proves correct over the archived holding window.</p>
      <ul>
        {''.join(metrics)}
      </ul>
    </div>
    <div class="card">
      <h2>Forecast Target</h2>
      <p>Submit a <code>binary_probability</code> forecast for target <code>{TARGET_NAME}</code>, where YES means the imported signal direction was correct over the configured holding horizon.</p>
      {report_note}
    </div>
  </body>
</html>
"""


def render_scenario_json(signal: ImportedSignal, *, has_daily_report: bool) -> dict[str, Any]:
    return {
        "source_project": "futures-flow",
        "source_signal_id": signal.signal_id,
        "scenario_id": signal.scenario_id,
        "signal_date": signal.signal_date,
        "signal_time": signal.signal_time,
        "direction": signal.direction,
        "strategy": signal.strategy,
        "entry_price": signal.entry_price,
        "confidence": signal.confidence,
        "ofi_value": signal.ofi_value,
        "cvd_value": signal.cvd_value,
        "atr_value": signal.atr_value,
        "hold_bars": signal.hold_bars,
        "target_price": signal.target_price,
        "resolved_at": signal.resolved_at,
        "params_source": signal.params_source,
        "macro_regime": signal.macro_regime,
        "daily_report_available": has_daily_report,
    }


def build_env_files(env_dir: Path) -> None:
    scripts_dir = env_dir / "scripts"
    tasks_dir = env_dir / "tasks"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir.mkdir(parents=True, exist_ok=True)

    write_json(
        env_dir / "env.json",
        {
            "id": "futures_flow_env@0.1",
            "version": "0.1",
            "base": "ubuntu-gnome-systemd_highres",
            "description": "Replay environment generated from resolved futures-flow directional signals.",
            "category": ["forecasting", "research", "browser", "desktop", "finance"],
            "tags": ["forecasting", "futures", "order-flow", "replay", "browser"],
            "resources": {"cpu": 2, "mem_gb": 4, "gpu": 0, "net": False},
            "observation": [{"type": "rgb_screen", "fps": 10, "resolution": [1920, 1080], "inline": False}],
            "action": [{"type": "mouse"}, {"type": "keyboard"}],
            "synchronous": True,
            "step_cycle_ms": 200,
            "recording": {
                "enable": True,
                "output_dir": "benchmarks/forecasting_world/environments/futures_flow_env/artifacts",
            },
            "vnc": {"enable": True, "host_port": 5971, "password": "password"},
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
                    "source": "benchmarks/forecasting_world/environments/futures_flow_env/scripts",
                    "target": "/workspace/scripts",
                    "mode": "ro",
                },
                {
                    "source": "benchmarks/forecasting_world/environments/futures_flow_env/tasks",
                    "target": "/workspace/tasks",
                    "mode": "ro",
                },
            ],
            "hooks": {
                "pre_start": "/workspace/scripts/install_futures_flow_env.sh",
                "post_start": "/workspace/scripts/setup_futures_flow_env.sh",
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
        scripts_dir / "install_futures_flow_env.sh",
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
        scripts_dir / "setup_futures_flow_env.sh",
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
    <title>Futures Flow Replay Workspace</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 2rem auto; max-width: 900px; line-height: 1.5; color: #1f2937; }}
      .card {{ border: 1px solid #d1d5db; border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 1rem; background: #f9fafb; }}
      code {{ background: #eef2ff; padding: 0.1rem 0.3rem; border-radius: 4px; }}
    </style>
  </head>
  <body>
    <h1>Futures Flow Replay Workspace</h1>
    <div class="card">
      <p>This environment replays resolved directional futures signals imported from <code>futures-flow</code>.</p>
      <p>After a task reset, open its page at <code>http://127.0.0.1:{LOCAL_PORT}/&lt;task_id&gt;/</code>.</p>
      <p>Forecast outputs belong under <code>{FORECAST_ROOT}/</code>.</p>
    </div>
  </body>
</html>
EOF

cat > /home/ga/Desktop/open_futures_flow_workspace.sh <<'EOF'
#!/bin/bash
set -euo pipefail
xdg-open "http://127.0.0.1:{LOCAL_PORT}/"
EOF
chmod +x /home/ga/Desktop/open_futures_flow_workspace.sh

cat > /home/ga/Desktop/Futures\\ Flow\\ Workspace.desktop <<'EOF'
[Desktop Entry]
Type=Application
Version=1.0
Name=Futures Flow Workspace
Comment=Open the local futures replay workspace
Exec=/home/ga/Desktop/open_futures_flow_workspace.sh
Terminal=false
Categories=Education;Science;
EOF
chmod +x /home/ga/Desktop/Futures\\ Flow\\ Workspace.desktop

if [ -f /tmp/{ENV_NAME}/research_server.pid ]; then
  old_pid="$(cat /tmp/{ENV_NAME}/research_server.pid || true)"
  if [ -n "${{old_pid}}" ] && kill -0 "${{old_pid}}" 2>/dev/null; then
    kill "${{old_pid}}" || true
  fi
fi

sudo -u ga bash -lc 'cd {WORKSPACE_ROOT} && nohup python3 /workspace/scripts/serve_research_workspace.py --root {WORKSPACE_ROOT} --port {LOCAL_PORT} >/tmp/{ENV_NAME}/research_server.log 2>&1 & echo $! >/tmp/{ENV_NAME}/research_server.pid'

chown -R ga:ga {WORKSPACE_ROOT} {FORECAST_ROOT} /tmp/{ENV_NAME}
chown ga:ga /home/ga/Desktop/open_futures_flow_workspace.sh /home/ga/Desktop/Futures\\ Flow\\ Workspace.desktop
""",
    )


def render_setup_script(signal: ImportedSignal, *, include_report: bool) -> str:
    copy_report = ""
    report_link = ""
    if include_report:
        copy_report = 'cp "/workspace/tasks/${TASK_ID}/report.html" "${TASK_ROOT}/report.html"\n'
        report_link = '        <li><a href="./report.html">Imported daily ES signal report</a></li>\n'

    return f"""#!/bin/bash
set -euo pipefail

TASK_ID="{signal.task_id}"
TASK_ROOT="{WORKSPACE_ROOT}/${{TASK_ID}}"
FORECAST_PATH="{FORECAST_ROOT}/${{TASK_ID}}_forecast.json"
mkdir -p "$TASK_ROOT" "{FORECAST_ROOT}"
cp "/workspace/tasks/${{TASK_ID}}/scenario.json" "${{TASK_ROOT}}/scenario.json"
cp "/workspace/tasks/${{TASK_ID}}/dossier.html" "${{TASK_ROOT}}/dossier.html"
{copy_report}cat > "${{TASK_ROOT}}/README.txt" <<EOF
Review dossier.html and scenario.json, then save your forecast to:
${{FORECAST_PATH}}

Browser workspace:
http://127.0.0.1:{LOCAL_PORT}/${{TASK_ID}}/

Expected schema:
{{
  "scenario_id": "{signal.scenario_id}",
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
        <li><a href="./dossier.html">Imported signal dossier</a></li>
        <li><a href="./scenario.json">Scenario metadata</a></li>
{report_link}        <li><a href="./README.txt">Task instructions</a></li>
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
    decision_score,
    load_exported_forecast,
    load_exported_result,
    load_hidden_outcome,
    probability_score,
    validate_submission,
)


def verify_imported_futures_flow_task(traj, env_info, task_info):
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

    if "market_implied_probability" in outcome and outcome["market_implied_probability"] is not None:
        decision_quality, recommended_action = decision_score(
            forecast_probability,
            float(outcome["market_implied_probability"]),
            normalized.get("decision"),
            threshold=float(outcome.get("decision_threshold", 0.05)),
        )
        final_score = combine_weighted_scores([(quality_score, 0.7), (decision_quality, 0.2), (completion_score, 0.1)])
        feedback.append(f"Decision={normalized.get('decision') or 'missing'}")
        feedback.append(f"Recommended action={recommended_action}")
        feedback.append(f"Decision quality={decision_quality:.1f}")
    else:
        final_score = combine_weighted_scores([(quality_score, 0.85), (completion_score, 0.15)])

    feedback.append(f"Probability={forecast_probability:.3f}")
    feedback.append(f"Outcome={outcome_value}")
    feedback.append(f"Forecast quality={quality_score:.1f}")
    return {
        "passed": final_score >= metadata.get("pass_threshold", 65),
        "score": round(final_score),
        "feedback": build_feedback(feedback),
    }
"""


def build_task_files(env_dir: Path, datasets_dir: Path, signal: ImportedSignal, *, reports_dir: Path) -> None:
    task_dir = env_dir / "tasks" / signal.task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"es_signals_{signal.signal_date}.html"
    has_report = report_path.exists()

    write_json(
        task_dir / "task.json",
        {
            "id": f"{signal.task_id}@1",
            "version": "1.0",
            "env_id": "futures_flow_env@0.1",
            "description": (
                f"You are replaying a resolved futures-flow signal. Review the task workspace at "
                f"http://127.0.0.1:{LOCAL_PORT}/{signal.task_id}/ or the mirrored files under "
                f"{WORKSPACE_ROOT}/{signal.task_id}/, then save a forecast to "
                f"{FORECAST_ROOT}/{signal.task_id}_forecast.json. "
                f"Assign a probability to the binary target '{TARGET_NAME}'."
            ),
            "difficulty": "medium",
            "init": {"timeout_sec": 300, "max_steps": 45, "reward_type": "sparse"},
            "hooks": {
                "pre_task": f"/workspace/tasks/{signal.task_id}/setup_task.sh",
                "post_task": f"/workspace/tasks/{signal.task_id}/export_result.sh",
            },
            "metadata": {
                "scenario_id": signal.scenario_id,
                "forecast_path": f"{FORECAST_ROOT}/{signal.task_id}_forecast.json",
                "expected_task_type": "binary_probability",
                "expected_target": TARGET_NAME,
                "outcome_ref": f"futures_flow/{signal.task_id}.hidden.json",
                "pass_threshold": 65,
            },
            "success": {"mode": "program", "spec": {"program": "verifier.py::verify_imported_futures_flow_task"}},
        },
    )
    write_json(task_dir / "scenario.json", render_scenario_json(signal, has_daily_report=has_report))
    write_text(task_dir / "dossier.html", render_dossier_html(signal, has_daily_report=has_report))
    if has_report:
        write_text(task_dir / "report.html", report_path.read_text(encoding="utf-8"))
    write_text(task_dir / "setup_task.sh", render_setup_script(signal, include_report=has_report))
    write_text(
        task_dir / "export_result.sh",
        EXPORT_SCRIPT_TEMPLATE.format(task_id=signal.task_id, forecast_root=FORECAST_ROOT),
    )
    write_text(task_dir / "verifier.py", VERIFIER_TEMPLATE)

    write_json(
        datasets_dir / f"{signal.task_id}.hidden.json",
        {
            "scenario_id": signal.scenario_id,
            "source_project": "futures-flow",
            "source_signal_id": signal.signal_id,
            "outcome": int(signal.outcome),
            "outcome_price": signal.outcome_price,
            "outcome_return": signal.outcome_return,
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


def write_seed_manifest(env_dir: Path, signals: list[ImportedSignal]) -> None:
    payload = [
        {
            "task_id": signal.task_id,
            "source_signal_id": signal.signal_id,
            "signal_date": signal.signal_date,
            "signal_time": signal.signal_time,
            "direction": signal.direction,
            "strategy": signal.strategy,
        }
        for signal in signals
    ]
    write_json(env_dir / "tasks" / "seed_tasks.json", payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import resolved futures-flow signals into forecasting_world.")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    signals = load_importable_signals(args.db_path, limit=args.limit)
    env_dir = ROOT / "environments" / ENV_NAME
    datasets_dir = ROOT / "datasets" / "futures_flow"
    if env_dir.exists():
        shutil.rmtree(env_dir)
    if datasets_dir.exists():
        shutil.rmtree(datasets_dir)
    build_env_files(env_dir)
    datasets_dir.mkdir(parents=True, exist_ok=True)
    task_ids: list[str] = []
    for signal in signals:
        build_task_files(env_dir, datasets_dir, signal, reports_dir=args.reports_dir)
        task_ids.append(signal.task_id)

    write_seed_manifest(env_dir, signals)
    write_split_file(ROOT / "splits", task_ids)

    print(f"Imported {len(task_ids)} futures-flow tasks into {env_dir}")
    for signal in signals:
        print(f"- {signal.task_id}: signal {signal.signal_id} ({signal.signal_date} {signal.strategy} {signal.direction})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
