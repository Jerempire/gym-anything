#!/bin/bash
set -euo pipefail

TASK_ID="ffwf_silver-bullet_fold26"
FORECAST_PATH="/home/ga/Documents/FuturesWalkForwardForecasts/${TASK_ID}_forecast.json"
START_TS=$(cat /tmp/${TASK_ID}_start.txt 2>/dev/null || echo "0")
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
{
  "forecast_exists": $FORECAST_EXISTS,
  "forecast_size": $FORECAST_SIZE,
  "forecast_created_after_start": $FORECAST_CREATED_AFTER_START,
  "forecast_path": "/tmp/exported_forecast.json"
}
EOF
chmod 644 /tmp/task_result.json 2>/dev/null || true
chmod 644 /tmp/exported_forecast.json 2>/dev/null || true
