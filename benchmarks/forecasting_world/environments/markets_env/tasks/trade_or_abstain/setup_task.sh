#!/bin/bash
set -euo pipefail

TASK_ID="trade_or_abstain"
TASK_ROOT="/home/ga/Desktop/MarketTasks/${TASK_ID}"
FORECAST_PATH="/home/ga/Documents/MarketForecasts/${TASK_ID}_forecast.json"
mkdir -p "$TASK_ROOT" /home/ga/Documents/MarketForecasts
cp "/workspace/tasks/${TASK_ID}/scenario.json" "${TASK_ROOT}/scenario.json"
cat > "${TASK_ROOT}/README.txt" <<EOF
Read scenario.json and save your forecast to:
${FORECAST_PATH}

Expected schema:
{
  "scenario_id": "markets.trade.2026-003",
  "task_type": "binary_probability",
  "forecast": {
    "target": "target_hit_before_stop",
    "probability": 0.50
  },
  "decision": "abstain",
  "confidence": 0.50,
  "notes": "Short rationale"
}
EOF
rm -f "$FORECAST_PATH" /tmp/task_result.json /tmp/exported_forecast.json
date +%s > /tmp/${TASK_ID}_start.txt
chown -R ga:ga "$TASK_ROOT" /home/ga/Documents/MarketForecasts
