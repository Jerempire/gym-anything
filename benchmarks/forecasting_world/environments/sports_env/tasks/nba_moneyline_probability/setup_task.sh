#!/bin/bash
set -euo pipefail

TASK_ID="nba_moneyline_probability"
TASK_ROOT="/home/ga/Desktop/SportsTasks/${TASK_ID}"
FORECAST_PATH="/home/ga/Documents/SportsForecasts/${TASK_ID}_forecast.json"
mkdir -p "$TASK_ROOT" /home/ga/Documents/SportsForecasts
cp "/workspace/tasks/${TASK_ID}/scenario.json" "${TASK_ROOT}/scenario.json"
cat > "${TASK_ROOT}/README.txt" <<EOF
Read scenario.json and save your forecast to:
${FORECAST_PATH}

Expected schema:
{
  "scenario_id": "sports.nba.2026-001",
  "task_type": "binary_probability",
  "forecast": {
    "target": "home_team_win",
    "probability": 0.50
  },
  "confidence": 0.50,
  "notes": "Short rationale"
}
EOF
rm -f "$FORECAST_PATH" /tmp/task_result.json /tmp/exported_forecast.json
date +%s > /tmp/${TASK_ID}_start.txt
chown -R ga:ga "$TASK_ROOT" /home/ga/Documents/SportsForecasts
