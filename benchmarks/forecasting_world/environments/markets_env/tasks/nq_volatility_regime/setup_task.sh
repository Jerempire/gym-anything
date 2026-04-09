#!/bin/bash
set -euo pipefail

TASK_ID="nq_volatility_regime"
TASK_ROOT="/home/ga/Desktop/MarketTasks/${TASK_ID}"
FORECAST_PATH="/home/ga/Documents/MarketForecasts/${TASK_ID}_forecast.json"
mkdir -p "$TASK_ROOT" /home/ga/Documents/MarketForecasts
cp "/workspace/tasks/${TASK_ID}/scenario.json" "${TASK_ROOT}/scenario.json"
cat > "${TASK_ROOT}/README.txt" <<EOF
Read scenario.json and save your forecast to:
${FORECAST_PATH}

Expected schema:
{
  "scenario_id": "markets.nq.2026-002",
  "task_type": "multiclass_distribution",
  "forecast": {
    "target": "next_session_volatility_regime",
    "class_probabilities": {
      "low": 0.20,
      "medium": 0.50,
      "high": 0.30
    }
  },
  "confidence": 0.50,
  "notes": "Short rationale"
}
EOF
rm -f "$FORECAST_PATH" /tmp/task_result.json /tmp/exported_forecast.json
date +%s > /tmp/${TASK_ID}_start.txt
chown -R ga:ga "$TASK_ROOT" /home/ga/Documents/MarketForecasts
