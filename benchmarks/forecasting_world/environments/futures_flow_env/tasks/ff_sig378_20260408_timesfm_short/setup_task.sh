#!/bin/bash
set -euo pipefail

TASK_ID="ff_sig378_20260408_timesfm_short"
TASK_ROOT="/home/ga/Desktop/FuturesFlowTasks/${TASK_ID}"
FORECAST_PATH="/home/ga/Documents/FuturesFlowForecasts/${TASK_ID}_forecast.json"
mkdir -p "$TASK_ROOT" "/home/ga/Documents/FuturesFlowForecasts"
cp "/workspace/tasks/${TASK_ID}/scenario.json" "${TASK_ROOT}/scenario.json"
cp "/workspace/tasks/${TASK_ID}/dossier.html" "${TASK_ROOT}/dossier.html"
cp "/workspace/tasks/${TASK_ID}/report.html" "${TASK_ROOT}/report.html"
cat > "${TASK_ROOT}/README.txt" <<EOF
Review dossier.html and scenario.json, then save your forecast to:
${FORECAST_PATH}

Browser workspace:
http://127.0.0.1:8126/${TASK_ID}/

Expected schema:
{
  "scenario_id": "futures_flow.signal.378",
  "task_type": "binary_probability",
  "forecast": {
    "target": "signal_correct",
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
      <p>Forecast target: <code>signal_correct</code></p>
      <p>Forecast output path: <code>${FORECAST_PATH}</code></p>
    </div>
    <div class="card">
      <h2>Evidence</h2>
      <ul>
        <li><a href="./dossier.html">Imported signal dossier</a></li>
        <li><a href="./scenario.json">Scenario metadata</a></li>
        <li><a href="./report.html">Imported daily ES signal report</a></li>
        <li><a href="./README.txt">Task instructions</a></li>
      </ul>
    </div>
  </body>
</html>
EOF
rm -f "$FORECAST_PATH" /tmp/task_result.json /tmp/exported_forecast.json
date +%s > /tmp/${TASK_ID}_start.txt
chown -R ga:ga "$TASK_ROOT" "/home/ga/Documents/FuturesFlowForecasts"
