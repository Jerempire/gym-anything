#!/bin/bash
set -euo pipefail

mkdir -p /home/ga/Desktop/SportsTasks
mkdir -p /home/ga/Documents/SportsForecasts
rm -f /tmp/task_result.json /tmp/exported_forecast.json
chown -R ga:ga /home/ga/Desktop/SportsTasks /home/ga/Documents/SportsForecasts
