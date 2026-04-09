#!/bin/bash
set -euo pipefail

mkdir -p /home/ga/Desktop/PsychologyTasks
mkdir -p /home/ga/Documents/PsychologyForecasts
rm -f /tmp/task_result.json /tmp/exported_forecast.json
chown -R ga:ga /home/ga/Desktop/PsychologyTasks /home/ga/Documents/PsychologyForecasts
