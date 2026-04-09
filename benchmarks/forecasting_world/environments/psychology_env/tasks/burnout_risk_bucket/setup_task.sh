#!/bin/bash
set -euo pipefail

TASK_ID="burnout_risk_bucket"
TASK_ROOT="/home/ga/Desktop/PsychologyTasks/${TASK_ID}"
FORECAST_PATH="/home/ga/Documents/PsychologyForecasts/${TASK_ID}_forecast.json"
mkdir -p "$TASK_ROOT" /home/ga/Documents/PsychologyForecasts
cp "/workspace/tasks/${TASK_ID}/scenario.json" "${TASK_ROOT}/scenario.json"
cat > "${TASK_ROOT}/README.txt" <<EOF
Read scenario.json and save your forecast to:
${FORECAST_PATH}

Expected schema:
{
  "scenario_id": "psych.synthetic.2026-002",
  "task_type": "multiclass_distribution",
  "forecast": {
    "target": "burnout_risk_bucket",
    "class_probabilities": {
      "low": 0.15,
      "medium": 0.35,
      "high": 0.50
    }
  },
  "confidence": 0.50,
  "notes": "Short rationale"
}
EOF
rm -f "$FORECAST_PATH" /tmp/task_result.json /tmp/exported_forecast.json
date +%s > /tmp/${TASK_ID}_start.txt
chown -R ga:ga "$TASK_ROOT" /home/ga/Documents/PsychologyForecasts
