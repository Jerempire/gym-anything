#!/bin/bash
set -euo pipefail

mkdir -p /home/ga/Desktop/ForecastHubTasks
mkdir -p /home/ga/Documents/ForecastHubForecasts
mkdir -p /tmp/forecast_hub_env
rm -f /tmp/task_result.json /tmp/exported_forecast.json

cat > /home/ga/Desktop/ForecastHubTasks/index.html <<'EOF'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Forecast Hub Replay Workspace</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem auto; max-width: 900px; line-height: 1.5; color: #1f2937; }
      .card { border: 1px solid #d1d5db; border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 1rem; background: #f9fafb; }
      code { background: #eef2ff; padding: 0.1rem 0.3rem; border-radius: 4px; }
    </style>
  </head>
  <body>
    <h1>Forecast Hub Replay Workspace</h1>
    <div class="card">
      <p>This environment replays resolved questions imported from forecast-hub.</p>
      <p>After a task reset, open its page at <code>http://127.0.0.1:8124/&lt;task_id&gt;/</code>.</p>
      <p>Forecast outputs belong under <code>/home/ga/Documents/ForecastHubForecasts/</code>.</p>
    </div>
  </body>
</html>
EOF

cat > /home/ga/Desktop/open_forecast_hub_workspace.sh <<'EOF'
#!/bin/bash
set -euo pipefail
xdg-open "http://127.0.0.1:8124/"
EOF
chmod +x /home/ga/Desktop/open_forecast_hub_workspace.sh

cat > /home/ga/Desktop/Forecast\ Hub\ Workspace.desktop <<'EOF'
[Desktop Entry]
Type=Application
Version=1.0
Name=Forecast Hub Workspace
Comment=Open the local forecast-hub replay workspace
Exec=/home/ga/Desktop/open_forecast_hub_workspace.sh
Terminal=false
Categories=Education;Science;
EOF
chmod +x /home/ga/Desktop/Forecast\ Hub\ Workspace.desktop

if [ -f /tmp/forecast_hub_env/research_server.pid ]; then
  old_pid="$(cat /tmp/forecast_hub_env/research_server.pid || true)"
  if [ -n "${old_pid}" ] && kill -0 "${old_pid}" 2>/dev/null; then
    kill "${old_pid}" || true
  fi
fi

sudo -u ga bash -lc 'cd /home/ga/Desktop/ForecastHubTasks && nohup python3 /workspace/scripts/serve_research_workspace.py --root /home/ga/Desktop/ForecastHubTasks --port 8124 >/tmp/forecast_hub_env/research_server.log 2>&1 & echo $! >/tmp/forecast_hub_env/research_server.pid'

chown -R ga:ga /home/ga/Desktop/ForecastHubTasks /home/ga/Documents/ForecastHubForecasts /tmp/forecast_hub_env
chown ga:ga /home/ga/Desktop/open_forecast_hub_workspace.sh /home/ga/Desktop/Forecast\ Hub\ Workspace.desktop
