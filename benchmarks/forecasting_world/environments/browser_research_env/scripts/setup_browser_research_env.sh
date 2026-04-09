#!/bin/bash
set -euo pipefail

mkdir -p /home/ga/Desktop/ResearchTasks
mkdir -p /home/ga/Documents/ResearchForecasts
mkdir -p /tmp/forecasting_world
rm -f /tmp/task_result.json /tmp/exported_forecast.json

cat > /home/ga/Desktop/ResearchTasks/index.html <<'EOF'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Forecasting Research Workspace</title>
    <style>
      body {
        font-family: Arial, sans-serif;
        margin: 2rem auto;
        max-width: 900px;
        line-height: 1.5;
        color: #1f2937;
      }
      .card {
        border: 1px solid #d1d5db;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        margin-bottom: 1rem;
        background: #f9fafb;
      }
      code {
        background: #eef2ff;
        padding: 0.1rem 0.3rem;
        border-radius: 4px;
      }
      a {
        color: #1d4ed8;
      }
    </style>
  </head>
  <body>
    <h1>Forecasting Research Workspace</h1>
    <div class="card">
      <p>This environment serves frozen browser-style research tasks over local HTTP.</p>
      <p>After a task reset, open its page at <code>http://127.0.0.1:8123/&lt;task_id&gt;/</code>.</p>
      <p>Forecast outputs belong under <code>/home/ga/Documents/ResearchForecasts/</code>.</p>
    </div>
    <div class="card">
      <h2>Task pages</h2>
      <ul>
        <li><a href="./event_probability_from_dossier/">event_probability_from_dossier</a></li>
        <li><a href="./linked_market_edge_decision/">linked_market_edge_decision</a></li>
        <li><a href="./forecast_revision_after_new_report/">forecast_revision_after_new_report</a></li>
      </ul>
      <p>If a page is missing, reset that task first.</p>
    </div>
  </body>
</html>
EOF

cat > /home/ga/Desktop/open_research_workspace.sh <<'EOF'
#!/bin/bash
set -euo pipefail
xdg-open "http://127.0.0.1:8123/"
EOF
chmod +x /home/ga/Desktop/open_research_workspace.sh

cat > /home/ga/Desktop/Research\ Workspace.desktop <<'EOF'
[Desktop Entry]
Type=Application
Version=1.0
Name=Research Workspace
Comment=Open the local forecasting research workspace
Exec=/home/ga/Desktop/open_research_workspace.sh
Terminal=false
Categories=Education;Science;
EOF
chmod +x /home/ga/Desktop/Research\ Workspace.desktop

if [ -f /tmp/forecasting_world/research_server.pid ]; then
  old_pid="$(cat /tmp/forecasting_world/research_server.pid || true)"
  if [ -n "${old_pid}" ] && kill -0 "${old_pid}" 2>/dev/null; then
    kill "${old_pid}" || true
  fi
fi

sudo -u ga bash -lc 'cd /home/ga/Desktop/ResearchTasks && nohup python3 /workspace/scripts/serve_research_workspace.py --root /home/ga/Desktop/ResearchTasks --port 8123 >/tmp/forecasting_world/research_server.log 2>&1 & echo $! >/tmp/forecasting_world/research_server.pid'

chown -R ga:ga /home/ga/Desktop/ResearchTasks /home/ga/Documents/ResearchForecasts /tmp/forecasting_world
chown ga:ga /home/ga/Desktop/open_research_workspace.sh /home/ga/Desktop/Research\ Workspace.desktop
