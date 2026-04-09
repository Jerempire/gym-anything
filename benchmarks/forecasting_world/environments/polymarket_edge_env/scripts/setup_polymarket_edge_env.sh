#!/bin/bash
set -euo pipefail

mkdir -p /home/ga/Desktop/PolymarketEdgeTasks
mkdir -p /home/ga/Documents/PolymarketEdgeForecasts
mkdir -p /tmp/polymarket_edge_env
rm -f /tmp/task_result.json /tmp/exported_forecast.json

cat > /home/ga/Desktop/PolymarketEdgeTasks/index.html <<'EOF'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Polymarket Edge Replay Workspace</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem auto; max-width: 900px; line-height: 1.5; color: #1f2937; }
      .card { border: 1px solid #d1d5db; border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 1rem; background: #f9fafb; }
      code { background: #eef2ff; padding: 0.1rem 0.3rem; border-radius: 4px; }
    </style>
  </head>
  <body>
    <h1>Polymarket Edge Replay Workspace</h1>
    <div class="card">
      <p>This environment replays resolved Polymarket markets imported from <code>polymarket-edge</code>.</p>
      <p>After a task reset, open its page at <code>http://127.0.0.1:8125/&lt;task_id&gt;/</code>.</p>
      <p>Forecast outputs belong under <code>/home/ga/Documents/PolymarketEdgeForecasts/</code>.</p>
    </div>
  </body>
</html>
EOF

cat > /home/ga/Desktop/open_polymarket_edge_workspace.sh <<'EOF'
#!/bin/bash
set -euo pipefail
xdg-open "http://127.0.0.1:8125/"
EOF
chmod +x /home/ga/Desktop/open_polymarket_edge_workspace.sh

cat > /home/ga/Desktop/Polymarket\ Edge\ Workspace.desktop <<'EOF'
[Desktop Entry]
Type=Application
Version=1.0
Name=Polymarket Edge Workspace
Comment=Open the local Polymarket replay workspace
Exec=/home/ga/Desktop/open_polymarket_edge_workspace.sh
Terminal=false
Categories=Education;Science;
EOF
chmod +x /home/ga/Desktop/Polymarket\ Edge\ Workspace.desktop

if [ -f /tmp/polymarket_edge_env/research_server.pid ]; then
  old_pid="$(cat /tmp/polymarket_edge_env/research_server.pid || true)"
  if [ -n "${old_pid}" ] && kill -0 "${old_pid}" 2>/dev/null; then
    kill "${old_pid}" || true
  fi
fi

sudo -u ga bash -lc 'cd /home/ga/Desktop/PolymarketEdgeTasks && nohup python3 /workspace/scripts/serve_research_workspace.py --root /home/ga/Desktop/PolymarketEdgeTasks --port 8125 >/tmp/polymarket_edge_env/research_server.log 2>&1 & echo $! >/tmp/polymarket_edge_env/research_server.pid'

chown -R ga:ga /home/ga/Desktop/PolymarketEdgeTasks /home/ga/Documents/PolymarketEdgeForecasts /tmp/polymarket_edge_env
chown ga:ga /home/ga/Desktop/open_polymarket_edge_workspace.sh /home/ga/Desktop/Polymarket\ Edge\ Workspace.desktop
