from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
from storage.events import load
import os

app = Flask(__name__)
CORS(app)

HTML = '''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ERC-20 Security Monitor</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #0f1117; color: #e2e8f0; min-height: 100vh; padding: 2rem; }
  h1 { font-size: 1.4rem; font-weight: 600; margin-bottom: 0.25rem; }
  .sub { font-size: 0.8rem; color: #94a3b8; margin-bottom: 2rem; display: flex; align-items: center; gap: 6px; }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: #22c55e; animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
  .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 1.5rem; }
  .metric { background: #1e2330; border-radius: 10px; padding: 1rem; }
  .metric .label { font-size: 11px; color: #64748b; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.05em; }
  .metric .value { font-size: 2rem; font-weight: 600; }
  .metric .vsub { font-size: 11px; color: #475569; margin-top: 4px; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 1.5rem; }
  .card { background: #1e2330; border-radius: 10px; padding: 1.25rem; }
  .card-title { font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 1rem; }
  .alert-row { display: flex; align-items: flex-start; gap: 10px; padding: 10px 0; border-bottom: 1px solid #2d3748; font-size: 13px; }
  .alert-row:last-child { border-bottom: none; }
  .alert-icon { width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0; }
  .icon-token { background: #1e3a5f; }
  .icon-drain { background: #3b1a1a; }
  .icon-approval { background: #3b2e00; }
  .icon-start { background: #1a3b2a; }
  .alert-body { flex: 1; }
  .alert-title { font-weight: 500; color: #e2e8f0; margin-bottom: 2px; }
  .alert-detail { color: #64748b; font-size: 11px; font-family: monospace; }
  .alert-block { font-size: 11px; color: #475569; white-space: nowrap; }
  .tg-bubble { background: #2d3748; border-radius: 12px 12px 12px 2px; padding: 10px 14px; font-size: 12px; margin-bottom: 8px; line-height: 1.6; }
  .tg-bubble.drain { border-left: 3px solid #ef4444; }
  .tg-bubble.approval { border-left: 3px solid #f59e0b; }
  .tg-bubble.token { border-left: 3px solid #3b82f6; }
  .mono { font-family: monospace; font-size: 11px; color: #94a3b8; }
  .empty { color: #475569; font-size: 13px; text-align: center; padding: 2rem; }
  @media (max-width: 700px) { .grid-4 { grid-template-columns: repeat(2,1fr); } .grid-2 { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<h1>ERC-20 Security Monitor</h1>
<div class="sub"><span class="dot"></span> Live · Ethereum Mainnet · Auto-refreshes every 5s</div>

<div class="grid-4">
  <div class="metric">
    <div class="label">Tokens found</div>
    <div class="value" id="tokensVal" style="color:#3b82f6;">0</div>
    <div class="vsub">auto-discovered</div>
  </div>
  <div class="metric">
    <div class="label">Transfers seen</div>
    <div class="value" id="transfersVal" style="color:#e2e8f0;">0</div>
    <div class="vsub">since start</div>
  </div>
  <div class="metric">
    <div class="label">Drain alerts</div>
    <div class="value" id="drainsVal" style="color:#ef4444;">0</div>
    <div class="vsub">large transfers</div>
  </div>
  <div class="metric">
    <div class="label">Unlimited approvals</div>
    <div class="value" id="approvalsVal" style="color:#f59e0b;">0</div>
    <div class="vsub">MAX_UINT256</div>
  </div>
</div>

<div class="grid-2">
  <div class="card">
    <div class="card-title">Live alert feed</div>
    <div id="alertFeed"><div class="empty">Waiting for events...</div></div>
  </div>
  <div class="card">
    <div class="card-title">Telegram messages preview</div>
    <div id="tgFeed"><div class="empty">No alerts yet...</div></div>
  </div>
</div>

<script>
const icons = { token: "N", drain: "D", approval: "!", start: "+" };
const tgClass = { drain: "drain", approval: "approval", token: "token", start: "" };

async function refresh() {
  try {
    const r = await fetch("/api/data");
    const d = await r.json();

    document.getElementById("tokensVal").textContent = d.stats.tokens;
    document.getElementById("transfersVal").textContent = d.stats.transfers.toLocaleString();
    document.getElementById("drainsVal").textContent = d.stats.drains;
    document.getElementById("approvalsVal").textContent = d.stats.approvals;

    const feed = document.getElementById("alertFeed");
    const tg = document.getElementById("tgFeed");

    if (d.alerts.length === 0) {
      feed.innerHTML = "<div class=\\"empty\\">Waiting for events...</div>";
      tg.innerHTML = "<div class=\\"empty\\">No alerts yet...</div>";
      return;
    }

    feed.innerHTML = d.alerts.slice(0, 8).map(a => `
      <div class="alert-row">
        <div class="alert-icon icon-${a.type}">${icons[a.type] || "?"}</div>
        <div class="alert-body">
          <div class="alert-title">${a.title}</div>
          <div class="alert-detail">${a.detail}</div>
        </div>
        <div class="alert-block">block ${a.block}</div>
      </div>`).join("");

    tg.innerHTML = d.alerts.filter(a => a.type !== "transfer").slice(0, 4).map(a => `
      <div class="tg-bubble ${tgClass[a.type] || ""}">
        <strong>${a.title}</strong><br>
        <span class="mono">${a.detail}</span>
      </div>`).join("");

  } catch(e) { console.log("fetch error", e); }
}

refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>'''

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/data")
def api_data():
    return jsonify(load())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
