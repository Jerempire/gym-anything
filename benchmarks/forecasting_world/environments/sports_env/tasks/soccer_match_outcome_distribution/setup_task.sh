#!/bin/bash
set -euo pipefail

TASK_ID="soccer_match_outcome_distribution"
TASK_ROOT="/home/ga/Desktop/SportsTasks/${TASK_ID}"
FORECAST_PATH="/home/ga/Documents/SportsForecasts/${TASK_ID}_forecast.json"
mkdir -p "$TASK_ROOT" /home/ga/Documents/SportsForecasts
cp "/workspace/tasks/${TASK_ID}/scenario.json" "${TASK_ROOT}/scenario.json"
cat > "${TASK_ROOT}/README.txt" <<EOF
Read scenario.json and save your forecast to:
${FORECAST_PATH}

Expected schema:
{
  "scenario_id": "sports.soccer.2026-003",
  "task_type": "multiclass_distribution",
  "forecast": {
    "target": "full_time_result",
    "class_probabilities": {
      "home_win": 0.45,
      "draw": 0.28,
      "away_win": 0.27
    }
  },
  "confidence": 0.50,
  "notes": "Short rationale"
}
EOF
rm -f "$FORECAST_PATH" /tmp/task_result.json /tmp/exported_forecast.json
date +%s > /tmp/${TASK_ID}_start.txt
chown -R ga:ga "$TASK_ROOT" /home/ga/Documents/SportsForecasts
