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
ENV_NAME = "polymarket_edge_env"
TARGET_NAME = "market_resolves_yes"
DEFAULT_JSON_PATH = Path.home() / "Projects" / "finance" / "polymarket-edge" / "data" / "resolved_markets.json"
WORKSPACE_ROOT = "/home/ga/Desktop/PolymarketEdgeTasks"
FORECAST_ROOT = "/home/ga/Documents/PolymarketEdgeForecasts"
LOCAL_PORT = 8125


@dataclass
class ImportedMarket:
    market_id: str
    question: str
    description: str
    slug: str
    category: str
    end_date: str | None
    market_type: str | None
    volume: float
    liquidity: float
    last_trade_price: float | None
    best_bid: float | None
    best_ask: float | None
    outcome: float

    @property
    def task_id(self) -> str:
        return f"pm_m{self.market_id}_{slugify(self.slug or self.question, max_len=44)}"

    @property
    def scenario_id(self) -> str:
        return f"polymarket_edge.market.{self.market_id}"


def slugify(text: str, *, max_len: int = 48) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not normalized:
        normalized = "market"
    return normalized[:max_len].rstrip("-")


def coerce_float(value: Any) -> float | None:
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def load_importable_markets(json_path: Path, *, limit: int) -> list[ImportedMarket]:
    rows = json.loads(json_path.read_text(encoding="utf-8"))
    candidates = [
        row
        for row in rows
        if row.get("question")
        and row.get("description")
        and isinstance(row.get("_resolved_yes"), bool)
        and row.get("id")
    ]
    candidates.sort(
        key=lambda row: (
            row.get("endDate") or "",
            coerce_float(row.get("volume")) or 0.0,
        ),
        reverse=True,
    )

    imported: list[ImportedMarket] = []
    seen_questions: set[str] = set()
    for row in candidates:
        dedupe_key = re.sub(r"\s+", " ", str(row["question"]).strip().lower())
        if dedupe_key in seen_questions:
            continue
        imported.append(
            ImportedMarket(
                market_id=str(row["id"]),
                question=str(row["question"]).strip(),
                description=str(row["description"]).strip(),
                slug=str(row.get("slug") or row["question"]).strip(),
                category=str(row.get("category") or "other").strip() or "other",
                end_date=row.get("endDate"),
                market_type=row.get("marketType"),
                volume=coerce_float(row.get("volume")) or 0.0,
                liquidity=coerce_float(row.get("liquidity")) or 0.0,
                last_trade_price=coerce_float(row.get("lastTradePrice")),
                best_bid=coerce_float(row.get("bestBid")),
                best_ask=coerce_float(row.get("bestAsk")),
                outcome=1.0 if row["_resolved_yes"] else 0.0,
            )
        )
        seen_questions.add(dedupe_key)
        if len(imported) >= limit:
            break
    return imported


def render_dossier_html(market: ImportedMarket) -> str:
    def metric(label: str, value: str) -> str:
        return f"<li><strong>{escape(label)}:</strong> {escape(value)}</li>"

    metrics = [
        metric("Category", market.category),
        metric("End date", market.end_date or "unknown"),
        metric("Market type", market.market_type or "unknown"),
        metric("Volume", f"{market.volume:,.0f}"),
        metric("Liquidity", f"{market.liquidity:,.0f}"),
        metric("Slug", market.slug),
    ]
    if market.last_trade_price is not None:
        metrics.append(metric("Last trade price", f"{market.last_trade_price:.3f}"))
    if market.best_bid is not None:
        metrics.append(metric("Best bid", f"{market.best_bid:.3f}"))
    if market.best_ask is not None:
        metrics.append(metric("Best ask", f"{market.best_ask:.3f}"))

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>{escape(market.question)}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 2rem auto; max-width: 980px; color: #1f2937; line-height: 1.5; }}
      .card {{ border: 1px solid #d1d5db; border-radius: 10px; padding: 1rem 1.25rem; background: #f9fafb; margin-bottom: 1rem; }}
      ul {{ padding-left: 1.2rem; }}
      code {{ background: #eef2ff; padding: 0.1rem 0.3rem; border-radius: 4px; }}
    </style>
  </head>
  <body>
    <h1>{escape(market.question)}</h1>
    <div class="card">
      <p>Replay a resolved Polymarket market. Your job is to assign your own probability that the market resolves YES using the archived prompt below.</p>
      <ul>
        {''.join(metrics)}
      </ul>
    </div>
    <div class="card">
      <h2>Resolution Criteria</h2>
      <p>{escape(market.description)}</p>
    </div>
    <div class="card">
      <h2>Forecast Task</h2>
      <p>Submit a <code>binary_probability</code> forecast for target <code>{TARGET_NAME}</code>.</p>
      <p>The hidden outcome is based on the resolved market result from <code>polymarket-edge</code>.</p>
    </div>
  </body>
</html>
"""


def render_scenario_json(market: ImportedMarket) -> dict[str, Any]:
    return {
        "source_project": "polymarket-edge",
        "source_market_id": market.market_id,
        "scenario_id": market.scenario_id,
        "question": market.question,
        "description": market.description,
        "slug": market.slug,
        "category": market.category,
        "end_date": market.end_date,
        "market_type": market.market_type,
        "volume": market.volume,
        "liquidity": market.liquidity,
        "last_trade_price": market.last_trade_price,
        "best_bid": market.best_bid,
        "best_ask": market.best_ask,
    }


def build_env_files(env_dir: Path) -> None:
    scripts_dir = env_dir / "scripts"
    tasks_dir = env_dir / "tasks"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir.mkdir(parents=True, exist_ok=True)

    write_json(
        env_dir / "env.json",
        {
            "id": "polymarket_edge_env@0.1",
            "version": "0.1",
            "base": "ubuntu-gnome-systemd_highres",
            "description": "Replay environment generated from resolved Polymarket markets imported from polymarket-edge.",
            "category": ["forecasting", "research", "browser", "desktop"],
            "tags": ["forecasting", "polymarket", "replay", "browser", "event-markets"],
            "resources": {"cpu": 2, "mem_gb": 4, "gpu": 0, "net": False},
            "observation": [{"type": "rgb_screen", "fps": 10, "resolution": [1920, 1080], "inline": False}],
            "action": [{"type": "mouse"}, {"type": "keyboard"}],
            "synchronous": True,
            "step_cycle_ms": 200,
            "recording": {
                "enable": True,
                "output_dir": "benchmarks/forecasting_world/environments/polymarket_edge_env/artifacts",
            },
            "vnc": {"enable": True, "host_port": 5970, "password": "password"},
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
                    "source": "benchmarks/forecasting_world/environments/polymarket_edge_env/scripts",
                    "target": "/workspace/scripts",
                    "mode": "ro",
                },
                {
                    "source": "benchmarks/forecasting_world/environments/polymarket_edge_env/tasks",
                    "target": "/workspace/tasks",
                    "mode": "ro",
                },
            ],
            "hooks": {
                "pre_start": "/workspace/scripts/install_polymarket_edge_env.sh",
                "post_start": "/workspace/scripts/setup_polymarket_edge_env.sh",
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
        scripts_dir / "install_polymarket_edge_env.sh",
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
        scripts_dir / "setup_polymarket_edge_env.sh",
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
    <title>Polymarket Edge Replay Workspace</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 2rem auto; max-width: 900px; line-height: 1.5; color: #1f2937; }}
      .card {{ border: 1px solid #d1d5db; border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 1rem; background: #f9fafb; }}
      code {{ background: #eef2ff; padding: 0.1rem 0.3rem; border-radius: 4px; }}
    </style>
  </head>
  <body>
    <h1>Polymarket Edge Replay Workspace</h1>
    <div class="card">
      <p>This environment replays resolved Polymarket markets imported from <code>polymarket-edge</code>.</p>
      <p>After a task reset, open its page at <code>http://127.0.0.1:{LOCAL_PORT}/&lt;task_id&gt;/</code>.</p>
      <p>Forecast outputs belong under <code>{FORECAST_ROOT}/</code>.</p>
    </div>
  </body>
</html>
EOF

cat > /home/ga/Desktop/open_polymarket_edge_workspace.sh <<'EOF'
#!/bin/bash
set -euo pipefail
xdg-open "http://127.0.0.1:{LOCAL_PORT}/"
EOF
chmod +x /home/ga/Desktop/open_polymarket_edge_workspace.sh

cat > /home/ga/Desktop/Polymarket\\ Edge\\ Workspace.desktop <<'EOF'
[Desktop Entry]
Type=Application
Version=1.0
Name=Polymarket Edge Workspace
Comment=Open the local Polymarket replay workspace
Exec=/home/ga/Desktop/open_polymarket_edge_workspace.sh
Terminal=false
Categories=Education;Science;
EOF
chmod +x /home/ga/Desktop/Polymarket\\ Edge\\ Workspace.desktop

if [ -f /tmp/{ENV_NAME}/research_server.pid ]; then
  old_pid="$(cat /tmp/{ENV_NAME}/research_server.pid || true)"
  if [ -n "${{old_pid}}" ] && kill -0 "${{old_pid}}" 2>/dev/null; then
    kill "${{old_pid}}" || true
  fi
fi

sudo -u ga bash -lc 'cd {WORKSPACE_ROOT} && nohup python3 /workspace/scripts/serve_research_workspace.py --root {WORKSPACE_ROOT} --port {LOCAL_PORT} >/tmp/{ENV_NAME}/research_server.log 2>&1 & echo $! >/tmp/{ENV_NAME}/research_server.pid'

chown -R ga:ga {WORKSPACE_ROOT} {FORECAST_ROOT} /tmp/{ENV_NAME}
chown ga:ga /home/ga/Desktop/open_polymarket_edge_workspace.sh /home/ga/Desktop/Polymarket\\ Edge\\ Workspace.desktop
""",
    )


def render_setup_script(market: ImportedMarket) -> str:
    return f"""#!/bin/bash
set -euo pipefail

TASK_ID="{market.task_id}"
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
  "scenario_id": "{market.scenario_id}",
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
        <li><a href="./dossier.html">Imported market dossier</a></li>
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
    decision_score,
    load_exported_forecast,
    load_exported_result,
    load_hidden_outcome,
    probability_score,
    validate_submission,
)


def verify_imported_polymarket_edge_task(traj, env_info, task_info):
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


def build_task_files(env_dir: Path, datasets_dir: Path, market: ImportedMarket) -> None:
    task_dir = env_dir / "tasks" / market.task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        task_dir / "task.json",
        {
            "id": f"{market.task_id}@1",
            "version": "1.0",
            "env_id": "polymarket_edge_env@0.1",
            "description": (
                f"You are replaying a resolved Polymarket market. Review the task workspace at "
                f"http://127.0.0.1:{LOCAL_PORT}/{market.task_id}/ or the mirrored files under "
                f"{WORKSPACE_ROOT}/{market.task_id}/, then save a forecast to "
                f"{FORECAST_ROOT}/{market.task_id}_forecast.json. "
                f"Assign a probability to the binary target '{TARGET_NAME}'."
            ),
            "difficulty": "medium",
            "init": {"timeout_sec": 300, "max_steps": 45, "reward_type": "sparse"},
            "hooks": {
                "pre_task": f"/workspace/tasks/{market.task_id}/setup_task.sh",
                "post_task": f"/workspace/tasks/{market.task_id}/export_result.sh",
            },
            "metadata": {
                "scenario_id": market.scenario_id,
                "forecast_path": f"{FORECAST_ROOT}/{market.task_id}_forecast.json",
                "expected_task_type": "binary_probability",
                "expected_target": TARGET_NAME,
                "outcome_ref": f"polymarket_edge/{market.task_id}.hidden.json",
                "pass_threshold": 65,
            },
            "success": {"mode": "program", "spec": {"program": "verifier.py::verify_imported_polymarket_edge_task"}},
        },
    )
    write_json(task_dir / "scenario.json", render_scenario_json(market))
    write_text(task_dir / "dossier.html", render_dossier_html(market))
    write_text(task_dir / "setup_task.sh", render_setup_script(market))
    write_text(
        task_dir / "export_result.sh",
        EXPORT_SCRIPT_TEMPLATE.format(task_id=market.task_id, forecast_root=FORECAST_ROOT),
    )
    write_text(task_dir / "verifier.py", VERIFIER_TEMPLATE)

    write_json(
        datasets_dir / f"{market.task_id}.hidden.json",
        {
            "scenario_id": market.scenario_id,
            "source_project": "polymarket-edge",
            "source_market_id": market.market_id,
            "outcome": int(market.outcome),
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


def write_seed_manifest(env_dir: Path, markets: list[ImportedMarket]) -> None:
    payload = [
        {
            "task_id": market.task_id,
            "source_market_id": market.market_id,
            "question": market.question,
            "category": market.category,
            "end_date": market.end_date,
        }
        for market in markets
    ]
    write_json(env_dir / "tasks" / "seed_tasks.json", payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import resolved Polymarket markets into forecasting_world.")
    parser.add_argument("--json-path", type=Path, default=DEFAULT_JSON_PATH)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    markets = load_importable_markets(args.json_path, limit=args.limit)
    env_dir = ROOT / "environments" / ENV_NAME
    datasets_dir = ROOT / "datasets" / "polymarket_edge"
    if env_dir.exists():
        shutil.rmtree(env_dir)
    if datasets_dir.exists():
        shutil.rmtree(datasets_dir)
    build_env_files(env_dir)
    datasets_dir.mkdir(parents=True, exist_ok=True)
    task_ids: list[str] = []
    for market in markets:
        build_task_files(env_dir, datasets_dir, market)
        task_ids.append(market.task_id)

    write_seed_manifest(env_dir, markets)
    write_split_file(ROOT / "splits", task_ids)

    print(f"Imported {len(task_ids)} polymarket-edge tasks into {env_dir}")
    for market in markets:
        print(f"- {market.task_id}: market {market.market_id} ({market.question})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
