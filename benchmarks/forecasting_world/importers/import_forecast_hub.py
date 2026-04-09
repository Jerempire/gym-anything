from __future__ import annotations

import argparse
import json
import re
import sqlite3
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENV_NAME = "forecast_hub_env"
TARGET_NAME = "question_resolves_yes"
DEFAULT_DB_PATH = Path.home() / "Projects" / "finance" / "forecast-hub" / "data" / "forecast.db"

MARKET_SOURCES = ("polymarket", "metaculus", "kalshi")
PREDICTION_SOURCES = ("consensus", "gemini", "grok", "user")
CONTEXT_SOURCES = ("substack_experts", "x_experts", "newsapi")


@dataclass
class ImportedQuestion:
    question_id: int
    text: str
    category: str
    status: str
    resolution_criteria: str
    resolution_date: str | None
    polymarket_slug: str | None
    resolved_at: str
    outcome: float
    signals: list[dict[str, Any]]
    predictions: list[dict[str, Any]]

    @property
    def task_id(self) -> str:
        slug = slugify(self.text, max_len=48)
        return f"fh_q{self.question_id}_{slug}"

    @property
    def scenario_id(self) -> str:
        return f"forecast_hub.question.{self.question_id}"


def slugify(text: str, *, max_len: int = 48) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not normalized:
        normalized = "question"
    return normalized[:max_len].rstrip("-")


def connect_readonly(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def fetch_latest_rows(
    conn: sqlite3.Connection,
    *,
    table: str,
    question_id: int,
    sources: tuple[str, ...],
    cutoff_ts: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in sources:
        row = conn.execute(
            f"""
            SELECT * FROM {table}
            WHERE question_id = ? AND source = ? AND timestamp <= ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (question_id, source, cutoff_ts),
        ).fetchone()
        if row is None:
            row = conn.execute(
                f"""
                SELECT * FROM {table}
                WHERE question_id = ? AND source = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (question_id, source),
            ).fetchone()
        if row is None:
            continue
        parsed = dict(row)
        if "evidence" in parsed and parsed["evidence"]:
            try:
                parsed["evidence"] = json.loads(parsed["evidence"])
            except json.JSONDecodeError:
                parsed["evidence"] = [parsed["evidence"]]
        elif "evidence" in parsed:
            parsed["evidence"] = []
        if "raw" in parsed and parsed["raw"]:
            try:
                parsed["raw"] = json.loads(parsed["raw"])
            except json.JSONDecodeError:
                pass
        rows.append(parsed)
    return rows


def load_importable_questions(db_path: Path, *, limit: int) -> list[ImportedQuestion]:
    conn = connect_readonly(db_path)
    try:
        rows = conn.execute(
            """
            SELECT *
            FROM questions
            WHERE outcome IN (0.0, 1.0)
              AND status IN ('resolved_yes', 'resolved_no')
            ORDER BY datetime(COALESCE(resolved_at, created_at)) DESC, id DESC
            LIMIT ?
            """,
            (limit * 3,),
        ).fetchall()

        imported: list[ImportedQuestion] = []
        seen_texts: set[str] = set()
        for row in rows:
            text = row["text"].strip()
            dedupe_key = re.sub(r"\s+", " ", text.lower())
            if dedupe_key in seen_texts:
                continue

            question_id = int(row["id"])
            resolved_at = row["resolved_at"] or row["created_at"]
            signals = fetch_latest_rows(
                conn,
                table="signals",
                question_id=question_id,
                sources=MARKET_SOURCES + CONTEXT_SOURCES,
                cutoff_ts=resolved_at,
            )
            predictions = fetch_latest_rows(
                conn,
                table="predictions",
                question_id=question_id,
                sources=PREDICTION_SOURCES,
                cutoff_ts=resolved_at,
            )
            if not signals and not predictions:
                continue

            imported.append(
                ImportedQuestion(
                    question_id=question_id,
                    text=text,
                    category=row["category"] or "other",
                    status=row["status"],
                    resolution_criteria=row["resolution_criteria"] or "",
                    resolution_date=row["resolution_date"],
                    polymarket_slug=row["polymarket_slug"],
                    resolved_at=resolved_at,
                    outcome=float(row["outcome"]),
                    signals=signals,
                    predictions=predictions,
                )
            )
            seen_texts.add(dedupe_key)
            if len(imported) >= limit:
                break
        return imported
    finally:
        conn.close()


def render_dossier_html(question: ImportedQuestion) -> str:
    def signal_card(signal: dict[str, Any]) -> str:
        evidence = signal.get("evidence") or []
        evidence_html = ""
        if evidence:
            items = "".join(f"<li>{escape(str(item))}</li>" for item in evidence[:5])
            evidence_html = f"<ul>{items}</ul>"
        return (
            "<div class='card'>"
            f"<h3>{escape(str(signal['source']))}</h3>"
            f"<p><strong>Probability:</strong> {float(signal['probability']):.1%}</p>"
            f"<p><strong>Confidence:</strong> {float(signal.get('confidence') or 0.5):.1%}</p>"
            f"<p><strong>Timestamp:</strong> {escape(str(signal.get('timestamp') or ''))}</p>"
            f"{evidence_html}"
            "</div>"
        )

    def prediction_card(prediction: dict[str, Any]) -> str:
        reasoning = escape(str(prediction.get("reasoning") or ""))
        if len(reasoning) > 800:
            reasoning = reasoning[:800] + "..."
        return (
            "<div class='card'>"
            f"<h3>{escape(str(prediction['source']))}</h3>"
            f"<p><strong>Probability:</strong> {float(prediction['probability']):.1%}</p>"
            f"<p><strong>Confidence:</strong> {float(prediction.get('confidence') or 0.5):.1%}</p>"
            f"<p><strong>Timestamp:</strong> {escape(str(prediction.get('timestamp') or ''))}</p>"
            f"<p>{reasoning or 'No reasoning captured.'}</p>"
            "</div>"
        )

    signal_cards = "\n".join(signal_card(signal) for signal in question.signals) or "<p>No market/context signals captured.</p>"
    prediction_cards = "\n".join(prediction_card(pred) for pred in question.predictions) or "<p>No model predictions captured.</p>"
    resolution_criteria = escape(question.resolution_criteria or "No explicit criteria recorded.")
    polymarket_slug = escape(question.polymarket_slug or "n/a")
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>{escape(question.text)}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 2rem auto; max-width: 1100px; color: #1f2937; line-height: 1.5; }}
      h1, h2 {{ margin-bottom: 0.5rem; }}
      .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1rem; }}
      .card {{ border: 1px solid #d1d5db; border-radius: 10px; padding: 1rem 1.25rem; background: #f9fafb; }}
      code {{ background: #eef2ff; padding: 0.1rem 0.3rem; border-radius: 4px; }}
    </style>
  </head>
  <body>
    <h1>{escape(question.text)}</h1>
    <div class="card">
      <p><strong>Category:</strong> {escape(question.category)}</p>
      <p><strong>Resolution date:</strong> {escape(question.resolution_date or "unknown")}</p>
      <p><strong>Resolved at:</strong> {escape(question.resolved_at)}</p>
      <p><strong>Polymarket slug:</strong> {polymarket_slug}</p>
      <p><strong>Resolution criteria:</strong> {resolution_criteria}</p>
      <p>Produce your own probability for whether this question resolves YES. Do not assume the source forecasts are correct.</p>
    </div>
    <h2>Market and context signals</h2>
    <div class="grid">
      {signal_cards}
    </div>
    <h2>Model forecasts from forecast-hub</h2>
    <div class="grid">
      {prediction_cards}
    </div>
  </body>
</html>
"""


def render_scenario_json(question: ImportedQuestion) -> dict[str, Any]:
    latest_market = next((signal for signal in question.signals if signal["source"] == "polymarket"), None)
    return {
        "source_project": "forecast-hub",
        "source_question_id": question.question_id,
        "scenario_id": question.scenario_id,
        "question": question.text,
        "category": question.category,
        "resolution_date": question.resolution_date,
        "resolution_criteria": question.resolution_criteria,
        "polymarket_slug": question.polymarket_slug,
        "latest_market_probability": latest_market["probability"] if latest_market else None,
        "signals": [
            {
                "source": signal["source"],
                "probability": signal["probability"],
                "confidence": signal.get("confidence"),
                "timestamp": signal.get("timestamp"),
                "evidence": signal.get("evidence") or [],
            }
            for signal in question.signals
        ],
        "predictions": [
            {
                "source": pred["source"],
                "probability": pred["probability"],
                "confidence": pred.get("confidence"),
                "timestamp": pred.get("timestamp"),
                "reasoning": pred.get("reasoning") or "",
            }
            for pred in question.predictions
        ],
    }


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def build_env_files(env_dir: Path) -> None:
    scripts_dir = env_dir / "scripts"
    tasks_dir = env_dir / "tasks"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir.mkdir(parents=True, exist_ok=True)

    write_json(
        env_dir / "env.json",
        {
            "id": "forecast_hub_env@0.1",
            "version": "0.1",
            "base": "ubuntu-gnome-systemd_highres",
            "description": "Replay environment generated from resolved forecast-hub questions and signal snapshots.",
            "category": ["forecasting", "research", "browser", "desktop"],
            "tags": ["forecasting", "forecast-hub", "replay", "browser", "polymarket"],
            "resources": {"cpu": 2, "mem_gb": 4, "gpu": 0, "net": False},
            "observation": [{"type": "rgb_screen", "fps": 10, "resolution": [1920, 1080], "inline": False}],
            "action": [{"type": "mouse"}, {"type": "keyboard"}],
            "synchronous": True,
            "step_cycle_ms": 200,
            "recording": {
                "enable": True,
                "output_dir": "benchmarks/forecasting_world/environments/forecast_hub_env/artifacts",
            },
            "vnc": {"enable": True, "host_port": 5969, "password": "password"},
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
                    "source": "benchmarks/forecasting_world/environments/forecast_hub_env/scripts",
                    "target": "/workspace/scripts",
                    "mode": "ro",
                },
                {
                    "source": "benchmarks/forecasting_world/environments/forecast_hub_env/tasks",
                    "target": "/workspace/tasks",
                    "mode": "ro",
                },
            ],
            "hooks": {
                "pre_start": "/workspace/scripts/install_forecast_hub_env.sh",
                "post_start": "/workspace/scripts/setup_forecast_hub_env.sh",
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
        scripts_dir / "install_forecast_hub_env.sh",
        """#!/bin/bash
set -euo pipefail

mkdir -p /home/ga/Desktop/ForecastHubTasks
mkdir -p /home/ga/Documents/ForecastHubForecasts
mkdir -p /tmp/forecast_hub_env
chown -R ga:ga /home/ga/Desktop/ForecastHubTasks /home/ga/Documents/ForecastHubForecasts /tmp/forecast_hub_env
""",
    )
    write_text(
        scripts_dir / "serve_research_workspace.py",
        (ROOT / "environments" / "browser_research_env" / "scripts" / "serve_research_workspace.py").read_text(encoding="utf-8"),
    )
    write_text(
        scripts_dir / "setup_forecast_hub_env.sh",
        """#!/bin/bash
set -euo pipefail

mkdir -p /home/ga/Desktop/ForecastHubTasks
mkdir -p /home/ga/Documents/ForecastHubForecasts
mkdir -p /tmp/forecast_hub_env
rm -f /tmp/task_result.json /tmp/exported_forecast.json

cat > /home/ga/Desktop/ForecastHubTasks/index.html <<'EOF'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Forecast Hub Replay Workspace</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem auto; max-width: 900px; line-height: 1.5; color: #1f2937; }
      .card { border: 1px solid #d1d5db; border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 1rem; background: #f9fafb; }
      code { background: #eef2ff; padding: 0.1rem 0.3rem; border-radius: 4px; }
    </style>
  </head>
  <body>
    <h1>Forecast Hub Replay Workspace</h1>
    <div class="card">
      <p>This environment replays resolved questions imported from forecast-hub.</p>
      <p>After a task reset, open its page at <code>http://127.0.0.1:8124/&lt;task_id&gt;/</code>.</p>
      <p>Forecast outputs belong under <code>/home/ga/Documents/ForecastHubForecasts/</code>.</p>
    </div>
  </body>
</html>
EOF

cat > /home/ga/Desktop/open_forecast_hub_workspace.sh <<'EOF'
#!/bin/bash
set -euo pipefail
xdg-open "http://127.0.0.1:8124/"
EOF
chmod +x /home/ga/Desktop/open_forecast_hub_workspace.sh

cat > /home/ga/Desktop/Forecast\\ Hub\\ Workspace.desktop <<'EOF'
[Desktop Entry]
Type=Application
Version=1.0
Name=Forecast Hub Workspace
Comment=Open the local forecast-hub replay workspace
Exec=/home/ga/Desktop/open_forecast_hub_workspace.sh
Terminal=false
Categories=Education;Science;
EOF
chmod +x /home/ga/Desktop/Forecast\\ Hub\\ Workspace.desktop

if [ -f /tmp/forecast_hub_env/research_server.pid ]; then
  old_pid="$(cat /tmp/forecast_hub_env/research_server.pid || true)"
  if [ -n "${old_pid}" ] && kill -0 "${old_pid}" 2>/dev/null; then
    kill "${old_pid}" || true
  fi
fi

sudo -u ga bash -lc 'cd /home/ga/Desktop/ForecastHubTasks && nohup python3 /workspace/scripts/serve_research_workspace.py --root /home/ga/Desktop/ForecastHubTasks --port 8124 >/tmp/forecast_hub_env/research_server.log 2>&1 & echo $! >/tmp/forecast_hub_env/research_server.pid'

chown -R ga:ga /home/ga/Desktop/ForecastHubTasks /home/ga/Documents/ForecastHubForecasts /tmp/forecast_hub_env
chown ga:ga /home/ga/Desktop/open_forecast_hub_workspace.sh /home/ga/Desktop/Forecast\\ Hub\\ Workspace.desktop
""",
    )


def render_setup_script(question: ImportedQuestion) -> str:
    return f"""#!/bin/bash
set -euo pipefail

TASK_ID="{question.task_id}"
TASK_ROOT="/home/ga/Desktop/ForecastHubTasks/${{TASK_ID}}"
FORECAST_PATH="/home/ga/Documents/ForecastHubForecasts/${{TASK_ID}}_forecast.json"
mkdir -p "$TASK_ROOT" /home/ga/Documents/ForecastHubForecasts
cp "/workspace/tasks/${{TASK_ID}}/scenario.json" "${{TASK_ROOT}}/scenario.json"
cp "/workspace/tasks/${{TASK_ID}}/dossier.html" "${{TASK_ROOT}}/dossier.html"
cat > "${{TASK_ROOT}}/README.txt" <<EOF
Review dossier.html and scenario.json, then save your forecast to:
${{FORECAST_PATH}}

Browser workspace:
http://127.0.0.1:8124/${{TASK_ID}}/

Expected schema:
{{
  "scenario_id": "{question.scenario_id}",
  "task_type": "binary_probability",
  "forecast": {{
    "target": "{TARGET_NAME}",
    "probability": 0.50
  }},
  "decision": "abstain",
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
        <li><a href="./dossier.html">Imported dossier</a></li>
        <li><a href="./scenario.json">Scenario metadata</a></li>
        <li><a href="./README.txt">Task instructions</a></li>
      </ul>
    </div>
  </body>
</html>
EOF
rm -f "$FORECAST_PATH" /tmp/task_result.json /tmp/exported_forecast.json
date +%s > /tmp/${{TASK_ID}}_start.txt
chown -R ga:ga "$TASK_ROOT" /home/ga/Documents/ForecastHubForecasts
"""


EXPORT_SCRIPT_TEMPLATE = """#!/bin/bash
set -euo pipefail

TASK_ID="{task_id}"
FORECAST_PATH="/home/ga/Documents/ForecastHubForecasts/${{TASK_ID}}_forecast.json"
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
"""


def build_task_files(env_dir: Path, datasets_dir: Path, question: ImportedQuestion) -> None:
    task_dir = env_dir / "tasks" / question.task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        task_dir / "task.json",
        {
            "id": f"{question.task_id}@1",
            "version": "1.0",
            "env_id": "forecast_hub_env@0.1",
            "description": (
                f"You are replaying a resolved forecast-hub question. Review the task workspace at "
                f"http://127.0.0.1:8124/{question.task_id}/ or the mirrored files under "
                f"/home/ga/Desktop/ForecastHubTasks/{question.task_id}/, then save a forecast to "
                f"/home/ga/Documents/ForecastHubForecasts/{question.task_id}_forecast.json. "
                f"Assign a probability to the binary target '{TARGET_NAME}' and optionally include a "
                f"decision field set to one of ['long', 'short', 'abstain']."
            ),
            "difficulty": "medium",
            "init": {"timeout_sec": 300, "max_steps": 45, "reward_type": "sparse"},
            "hooks": {
                "pre_task": f"/workspace/tasks/{question.task_id}/setup_task.sh",
                "post_task": f"/workspace/tasks/{question.task_id}/export_result.sh",
            },
            "metadata": {
                "scenario_id": question.scenario_id,
                "forecast_path": f"/home/ga/Documents/ForecastHubForecasts/{question.task_id}_forecast.json",
                "expected_task_type": "binary_probability",
                "expected_target": TARGET_NAME,
                "outcome_ref": f"forecast_hub/{question.task_id}.hidden.json",
                "pass_threshold": 65,
            },
            "success": {"mode": "program", "spec": {"program": "verifier.py::verify_imported_forecast_hub_task"}},
        },
    )
    write_json(task_dir / "scenario.json", render_scenario_json(question))
    write_text(task_dir / "dossier.html", render_dossier_html(question))
    write_text(task_dir / "setup_task.sh", render_setup_script(question))
    write_text(task_dir / "export_result.sh", EXPORT_SCRIPT_TEMPLATE.format(task_id=question.task_id))
    write_text(task_dir / "verifier.py", VERIFIER_TEMPLATE)

    latest_market = next((signal for signal in question.signals if signal["source"] == "polymarket"), None)
    outcome_payload: dict[str, Any] = {
        "scenario_id": question.scenario_id,
        "source_project": "forecast-hub",
        "source_question_id": question.question_id,
        "outcome": int(question.outcome),
    }
    if latest_market is not None:
        outcome_payload["market_implied_probability"] = float(latest_market["probability"])
        outcome_payload["decision_threshold"] = 0.05
    write_json(datasets_dir / f"{question.task_id}.hidden.json", outcome_payload)


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


def write_seed_manifest(env_dir: Path, questions: list[ImportedQuestion]) -> None:
    payload = [
        {
            "task_id": question.task_id,
            "source_question_id": question.question_id,
            "text": question.text,
            "category": question.category,
            "resolved_at": question.resolved_at,
        }
        for question in questions
    ]
    write_json(env_dir / "tasks" / "seed_tasks.json", payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import resolved forecast-hub questions into forecasting_world.")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--limit", type=int, default=6)
    args = parser.parse_args()

    questions = load_importable_questions(args.db_path, limit=args.limit)
    env_dir = ROOT / "environments" / ENV_NAME
    datasets_dir = ROOT / "datasets" / "forecast_hub"
    build_env_files(env_dir)
    datasets_dir.mkdir(parents=True, exist_ok=True)
    task_ids: list[str] = []
    for question in questions:
        build_task_files(env_dir, datasets_dir, question)
        task_ids.append(question.task_id)

    write_seed_manifest(env_dir, questions)
    write_split_file(ROOT / "splits", task_ids)

    print(f"Imported {len(task_ids)} forecast-hub tasks into {env_dir}")
    for question in questions:
        print(f"- {question.task_id}: q{question.question_id} ({question.text})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
