#!/bin/bash
set -euo pipefail

TASK_ID="nfl_total_direction"
TASK_ROOT="/home/ga/Desktop/SportsTasks/${TASK_ID}"
FORECAST_PATH="/home/ga/Documents/SportsForecasts/${TASK_ID}_forecast.json"
mkdir -p "$TASK_ROOT" /home/ga/Documents/SportsForecasts
cp "/workspace/tasks/${TASK_ID}/scenario.json" "${TASK_ROOT}/scenario.json"
cat > "${TASK_ROOT}/README.txt" <<EOF
Read scenario.json and save your forecast to:
${FORECAST_PATH}

Expected schema:
{
  "scenario_id": "sports.nfl.2026-002",
  "task_type": "binary_probability",
  "forecast": {
    "target": "game_goes_over_total",
    "probability": 0.50
  },
  "confidence": 0.50,
  "notes": "Short rationale"
}
EOF
rm -f "$FORECAST_PATH" /tmp/task_result.json /tmp/exported_forecast.json
date +%s > /tmp/${TASK_ID}_start.txt
chown -R ga:ga "$TASK_ROOT" /home/ga/Documents/SportsForecasts
