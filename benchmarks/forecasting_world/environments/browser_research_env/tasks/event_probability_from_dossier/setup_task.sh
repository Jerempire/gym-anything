#!/bin/bash
set -euo pipefail

TASK_ID="event_probability_from_dossier"
TASK_ROOT="/home/ga/Desktop/ResearchTasks/${TASK_ID}"
FORECAST_PATH="/home/ga/Documents/ResearchForecasts/${TASK_ID}_forecast.json"
mkdir -p "$TASK_ROOT" /home/ga/Documents/ResearchForecasts
cp "/workspace/tasks/${TASK_ID}/scenario.json" "${TASK_ROOT}/scenario.json"
cp "/workspace/tasks/${TASK_ID}/dossier.html" "${TASK_ROOT}/dossier.html"
cat > "${TASK_ROOT}/README.txt" <<EOF
Review dossier.html and scenario.json, then save your forecast to:
${FORECAST_PATH}

Browser workspace:
http://127.0.0.1:8123/${TASK_ID}/

Expected schema:
{
  "scenario_id": "research.event.2026-001",
  "task_type": "binary_probability",
  "forecast": {
    "target": "policy_adopted_by_deadline",
    "probability": 0.50
  },
  "confidence": 0.50,
  "notes": "Short rationale"
}
EOF
cat > "${TASK_ROOT}/index.html" <<EOF
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>${TASK_ID}</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem auto; max-width: 960px; color: #1f2937; }
      .card { border: 1px solid #d1d5db; border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 1rem; background: #f9fafb; }
      code { background: #eef2ff; padding: 0.1rem 0.3rem; border-radius: 4px; }
      a { color: #1d4ed8; }
    </style>
  </head>
  <body>
    <h1>${TASK_ID}</h1>
    <div class="card">
      <p>Forecast target: <code>policy_adopted_by_deadline</code></p>
      <p>Forecast output path: <code>${FORECAST_PATH}</code></p>
    </div>
    <div class="card">
      <h2>Evidence</h2>
      <ul>
        <li><a href="./dossier.html">Dossier</a></li>
        <li><a href="./scenario.json">Scenario metadata</a></li>
        <li><a href="./README.txt">Task instructions</a></li>
      </ul>
    </div>
  </body>
</html>
EOF
rm -f "$FORECAST_PATH" /tmp/task_result.json /tmp/exported_forecast.json
date +%s > /tmp/${TASK_ID}_start.txt
chown -R ga:ga "$TASK_ROOT" /home/ga/Documents/ResearchForecasts
