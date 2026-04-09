#!/bin/bash
set -euo pipefail

mkdir -p /home/ga/Desktop/FuturesWalkForwardTasks
mkdir -p /home/ga/Documents/FuturesWalkForwardForecasts
mkdir -p /tmp/futures_walk_forward_env
rm -f /tmp/task_result.json /tmp/exported_forecast.json

cat > /home/ga/Desktop/FuturesWalkForwardTasks/index.html <<'EOF'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Futures Walk-Forward Workspace</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem auto; max-width: 900px; line-height: 1.5; color: #1f2937; }
      .card { border: 1px solid #d1d5db; border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 1rem; background: #f9fafb; }
      code { background: #eef2ff; padding: 0.1rem 0.3rem; border-radius: 4px; }
    </style>
  </head>
  <body>
    <h1>Futures Walk-Forward Workspace</h1>
    <div class="card">
      <p>This environment replays futures strategy walk-forward folds imported from <code>futures-flow</code>.</p>
      <p>After a task reset, open its page at <code>http://127.0.0.1:8127/&lt;task_id&gt;/</code>.</p>
      <p>Forecast outputs belong under <code>/home/ga/Documents/FuturesWalkForwardForecasts/</code>.</p>
    </div>
  </body>
</html>
EOF

cat > /home/ga/Desktop/open_futures_walk_forward_workspace.sh <<'EOF'
#!/bin/bash
set -euo pipefail
xdg-open "http://127.0.0.1:8127/"
EOF
chmod +x /home/ga/Desktop/open_futures_walk_forward_workspace.sh

cat > /home/ga/Desktop/Futures\ Walk\ Forward\ Workspace.desktop <<'EOF'
[Desktop Entry]
Type=Application
Version=1.0
Name=Futures Walk Forward Workspace
Comment=Open the local futures walk-forward workspace
Exec=/home/ga/Desktop/open_futures_walk_forward_workspace.sh
Terminal=false
Categories=Education;Science;
EOF
chmod +x /home/ga/Desktop/Futures\ Walk\ Forward\ Workspace.desktop

if [ -f /tmp/futures_walk_forward_env/research_server.pid ]; then
  old_pid="$(cat /tmp/futures_walk_forward_env/research_server.pid || true)"
  if [ -n "${old_pid}" ] && kill -0 "${old_pid}" 2>/dev/null; then
    kill "${old_pid}" || true
  fi
fi

sudo -u ga bash -lc 'cd /home/ga/Desktop/FuturesWalkForwardTasks && nohup python3 /workspace/scripts/serve_research_workspace.py --root /home/ga/Desktop/FuturesWalkForwardTasks --port 8127 >/tmp/futures_walk_forward_env/research_server.log 2>&1 & echo $! >/tmp/futures_walk_forward_env/research_server.pid'

chown -R ga:ga /home/ga/Desktop/FuturesWalkForwardTasks /home/ga/Documents/FuturesWalkForwardForecasts /tmp/futures_walk_forward_env
chown ga:ga /home/ga/Desktop/open_futures_walk_forward_workspace.sh /home/ga/Desktop/Futures\ Walk\ Forward\ Workspace.desktop
