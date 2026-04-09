#!/bin/bash
set -euo pipefail

mkdir -p /home/ga/Desktop/MarketTasks
mkdir -p /home/ga/Documents/MarketForecasts
rm -f /tmp/task_result.json /tmp/exported_forecast.json
chown -R ga:ga /home/ga/Desktop/MarketTasks /home/ga/Documents/MarketForecasts
