import os, json
from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

EVENTS_FILE = "/tmp/events.json"

def load():
    try:
        with open(EVENTS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"alerts": [], "stats": {"tokens": 0, "transfers": 0, "drains": 0, "approvals": 0}}

def save(data):
    with open(EVENTS_FILE, 'w') as f:
        json.dump(data, f)

HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ERC-20 Security Monitor</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Syne:wght@400;600;800&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #080b10;
  --surface: #0d1117;
  --surface2: #161b22;
  --border: #21262d;
  --border2: #30363d;
  --text: #e6edf3;
  --muted: #7d8590;
  --dim: #484f58;
  --green: #3fb950;
  --green-bg: #0d1f0f;
  --red: #f85149;
  --red-bg: #1f0d0d;
  --yellow: #d29922;
  --yellow-bg: #1f1a0d;
  --blue: #58a6ff;
  --blue-bg: #0d1526;
  --purple: #bc8cff;
  --purple-bg: #1a0d2e;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; }
body {
  font-family: 'Syne', sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  overflow-x: hidden;
}
.mono { font-family: 'JetBrains Mono', monospace; }

/* GRID SCAN BACKGROUND */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(63,185,80,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(63,185,80,0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 0;
}

.app { position: relative; z-index: 1; display: flex; flex-direction: column; min-height: 100vh; }

/* TOPBAR */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border);
  background: rgba(8,11,16,0.9);
  backdrop-filter: blur(12px);
  position: sticky;
  top: 0;
  z-index: 100;
}
.brand { display: flex; align-items: center; gap: 12px; }
.brand-icon {
  width: 36px; height: 36px;
  background: var(--green-bg);
  border: 1px solid var(--green);
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px;
}
.brand-name { font-size: 1rem; font-weight: 800; letter-spacing: -0.02em; }
.brand-sub { font-size: 11px; color: var(--muted); font-family: 'JetBrains Mono', monospace; margin-top: 1px; }
.topbar-right { display: flex; align-items: center; gap: 12px; }
.live-badge {
  display: flex; align-items: center; gap: 6px;
  background: var(--green-bg);
  border: 1px solid rgba(63,185,80,0.3);
  border-radius: 20px;
  padding: 4px 12px;
  font-size: 11px;
  font-weight: 600;
  color: var(--green);
  font-family: 'JetBrains Mono', monospace;
}
.live-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--green);
  animation: blink 1.4s infinite;
}
@keyframes blink { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.3;transform:scale(0.8)} }
.block-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--muted);
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 4px 10px;
}

/* MAIN LAYOUT */
.main { flex: 1; padding: 1.5rem; display: flex; flex-direction: column; gap: 1.25rem; }

/* STATS ROW */
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }
.stat-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.25rem;
  position: relative;
  overflow: hidden;
  transition: border-color 0.2s;
}
.stat-card:hover { border-color: var(--border2); }
.stat-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
}
.stat-card.tokens::before { background: var(--blue); }
.stat-card.transfers::before { background: var(--purple); }
.stat-card.drains::before { background: var(--red); }
.stat-card.approvals::before { background: var(--yellow); }
.stat-label { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 10px; font-family: 'JetBrains Mono', monospace; }
.stat-value { font-size: 2.2rem; font-weight: 800; line-height: 1; margin-bottom: 6px; }
.stat-card.tokens .stat-value { color: var(--blue); }
.stat-card.transfers .stat-value { color: var(--purple); }
.stat-card.drains .stat-value { color: var(--red); }
.stat-card.approvals .stat-value { color: var(--yellow); }
.stat-sub { font-size: 11px; color: var(--dim); font-family: 'JetBrains Mono', monospace; }

/* CONTENT GRID */
.content-grid { display: grid; grid-template-columns: 1fr 380px; gap: 1.25rem; flex: 1; }

/* PANEL */
.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border);
  background: var(--surface2);
  flex-shrink: 0;
}
.panel-title {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--muted);
  font-family: 'JetBrains Mono', monospace;
}
.panel-count {
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  color: var(--dim);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 2px 10px;
}

/* FILTER TABS */
.filter-tabs {
  display: flex;
  gap: 4px;
  padding: 0.75rem 1.25rem;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  flex-shrink: 0;
  overflow-x: auto;
}
.tab {
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  padding: 4px 12px;
  border-radius: 20px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}
.tab:hover { border-color: var(--border2); color: var(--text); }
.tab.active { background: var(--surface2); border-color: var(--border2); color: var(--text); }
.tab.active.all { border-color: var(--border2); }
.tab.active.token { border-color: var(--blue); color: var(--blue); background: var(--blue-bg); }
.tab.active.drain { border-color: var(--red); color: var(--red); background: var(--red-bg); }
.tab.active.approval { border-color: var(--yellow); color: var(--yellow); background: var(--yellow-bg); }
.tab.active.transfer { border-color: var(--purple); color: var(--purple); background: var(--purple-bg); }

/* ALERT FEED */
.feed-scroll {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  max-height: 520px;
}
.feed-scroll::-webkit-scrollbar { width: 4px; }
.feed-scroll::-webkit-scrollbar-track { background: transparent; }
.feed-scroll::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 4px; }

.alert-item {
  display: flex;
  gap: 12px;
  padding: 14px 1.25rem;
  border-bottom: 1px solid var(--border);
  transition: background 0.15s;
  animation: slideIn 0.3s ease;
}
@keyframes slideIn { from { opacity:0; transform: translateY(-8px); } to { opacity:1; transform: translateY(0); } }
.alert-item:hover { background: var(--surface2); }
.alert-item:last-child { border-bottom: none; }

.alert-dot {
  width: 32px; height: 32px;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 1px;
  font-family: 'JetBrains Mono', monospace;
}
.dot-token { background: var(--blue-bg); color: var(--blue); border: 1px solid rgba(88,166,255,0.2); }
.dot-drain { background: var(--red-bg); color: var(--red); border: 1px solid rgba(248,81,73,0.2); }
.dot-approval { background: var(--yellow-bg); color: var(--yellow); border: 1px solid rgba(210,153,34,0.2); }
.dot-transfer { background: var(--purple-bg); color: var(--purple); border: 1px solid rgba(188,140,255,0.2); }
.dot-start { background: var(--green-bg); color: var(--green); border: 1px solid rgba(63,185,80,0.2); }

.alert-body { flex: 1; min-width: 0; }
.alert-title { font-size: 13px; font-weight: 600; color: var(--text); margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.alert-detail { font-size: 11px; color: var(--muted); font-family: 'JetBrains Mono', monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.alert-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; flex-shrink: 0; }
.alert-block { font-size: 10px; font-family: 'JetBrains Mono', monospace; color: var(--dim); background: var(--surface2); border: 1px solid var(--border); border-radius: 4px; padding: 2px 6px; white-space: nowrap; }

/* EMPTY STATE */
.empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 3rem 1rem; gap: 12px; color: var(--dim);
}
.empty-icon { font-size: 2rem; opacity: 0.4; }
.empty-text { font-size: 13px; font-family: 'JetBrains Mono', monospace; }

/* SIDE PANEL - RECENT ALERTS SUMMARY */
.side-panel { display: flex; flex-direction: column; gap: 1.25rem; }

/* ACTIVITY LOG */
.activity-scroll {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  max-height: 420px;
}
.activity-scroll::-webkit-scrollbar { width: 4px; }
.activity-scroll::-webkit-scrollbar-track { background: transparent; }
.activity-scroll::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 4px; }

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 1.25rem;
  border-bottom: 1px solid var(--border);
  animation: slideIn 0.3s ease;
}
.activity-item:last-child { border-bottom: none; }
.activity-line { display: flex; flex-direction: column; flex: 1; min-width: 0; }
.activity-title { font-size: 12px; font-weight: 600; color: var(--text); margin-bottom: 2px; }
.activity-addr { font-size: 10px; font-family: 'JetBrains Mono', monospace; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.activity-block { font-size: 10px; font-family: 'JetBrains Mono', monospace; color: var(--dim); margin-top: 2px; }

/* STATUS FOOTER */
.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.6rem 1.5rem;
  border-top: 1px solid var(--border);
  background: var(--surface);
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  color: var(--dim);
}
.status-left { display: flex; align-items: center; gap: 16px; }
.status-item { display: flex; align-items: center; gap: 6px; }

@media (max-width: 900px) {
  .stats-row { grid-template-columns: repeat(2,1fr); }
  .content-grid { grid-template-columns: 1fr; }
  .side-panel { display: none; }
}
</style>
</head>
<body>
<div class="app">

  <!-- TOPBAR -->
  <div class="topbar">
    <div class="brand">
      <div class="brand-icon">🛡</div>
      <div>
        <div class="brand-name">ERC-20 Security Monitor</div>
        <div class="brand-sub mono">ethereum mainnet · auto-scan</div>
      </div>
    </div>
    <div class="topbar-right">
      <div class="block-badge mono" id="blockBadge">block —</div>
      <div class="live-badge"><span class="live-dot"></span>LIVE</div>
    </div>
  </div>

  <!-- MAIN -->
  <div class="main">

    <!-- STATS -->
    <div class="stats-row">
      <div class="stat-card tokens">
        <div class="stat-label">Tokens Discovered</div>
        <div class="stat-value mono" id="sTokens">0</div>
        <div class="stat-sub">auto-detected ERC20s</div>
      </div>
      <div class="stat-card transfers">
        <div class="stat-label">Transfers Scanned</div>
        <div class="stat-value mono" id="sTransfers">0</div>
        <div class="stat-sub">since monitor start</div>
      </div>
      <div class="stat-card drains">
        <div class="stat-label">Drain Alerts</div>
        <div class="stat-value mono" id="sDrains">0</div>
        <div class="stat-sub">threshold exceeded</div>
      </div>
      <div class="stat-card approvals">
        <div class="stat-label">Unlimited Approvals</div>
        <div class="stat-value mono" id="sApprovals">0</div>
        <div class="stat-sub">MAX_UINT256 detected</div>
      </div>
    </div>

    <!-- CONTENT GRID -->
    <div class="content-grid">

      <!-- MAIN FEED -->
      <div class="panel">
        <div class="panel-header">
          <span class="panel-title">Live Alert Feed</span>
          <span class="panel-count mono" id="feedCount">0 events</span>
        </div>
        <div class="filter-tabs">
          <button class="tab active all" onclick="setFilter('all',this)">All</button>
          <button class="tab" onclick="setFilter('token',this)">Tokens</button>
          <button class="tab" onclick="setFilter('drain',this)">Drains</button>
          <button class="tab" onclick="setFilter('approval',this)">Approvals</button>
          <button class="tab" onclick="setFilter('transfer',this)">Transfers</button>
        </div>
        <div class="feed-scroll" id="alertFeed">
          <div class="empty-state">
            <div class="empty-icon">📡</div>
            <div class="empty-text">Scanning mainnet for events...</div>
          </div>
        </div>
      </div>

      <!-- SIDE PANEL -->
      <div class="side-panel">
        <div class="panel" style="flex:1;">
          <div class="panel-header">
            <span class="panel-title">High Priority</span>
            <span class="panel-count mono" id="highCount">0</span>
          </div>
          <div class="activity-scroll" id="highFeed">
            <div class="empty-state" style="padding:2rem 1rem;">
              <div class="empty-icon" style="font-size:1.5rem;">🔍</div>
              <div class="empty-text">No high-priority alerts</div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>

  <!-- STATUS BAR -->
  <div class="status-bar">
    <div class="status-left">
      <div class="status-item"><span style="color:var(--green)">●</span> Connected to Ethereum Mainnet</div>
      <div class="status-item" id="lastUpdate">Last update: —</div>
    </div>
    <div>Refreshing every 5s</div>
  </div>

</div>

<script>
const ICONS = {token:'N', drain:'D', approval:'!', transfer:'T', start:'✓'};
const DOT_CLASS = {token:'dot-token', drain:'dot-drain', approval:'dot-approval', transfer:'dot-transfer', start:'dot-start'};
const TYPE_LABEL = {token:'NEW TOKEN', drain:'DRAIN', approval:'APPROVAL', transfer:'TRANSFER', start:'STARTED'};

let allAlerts = [];
let currentFilter = 'all';

function setFilter(f, el) {
  currentFilter = f;
  document.querySelectorAll('.tab').forEach(t => {
    t.className = 'tab';
  });
  el.className = `tab active ${f}`;
  renderFeed();
}

function timeAgo(ts) {
  if (!ts) return 'just now';
  const diff = Math.floor((Date.now() - ts) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
  return `${Math.floor(diff/3600)}h ago`;
}

function renderFeed() {
  const feed = document.getElementById('alertFeed');
  const filtered = currentFilter === 'all' ? allAlerts : allAlerts.filter(a => a.type === currentFilter);
  document.getElementById('feedCount').textContent = `${filtered.length} events`;

  if (!filtered.length) {
    feed.innerHTML = `<div class="empty-state"><div class="empty-icon">📡</div><div class="empty-text">No ${currentFilter === 'all' ? '' : currentFilter + ' '}events yet...</div></div>`;
    return;
  }

  feed.innerHTML = filtered.map(a => `
    <div class="alert-item">
      <div class="alert-dot ${DOT_CLASS[a.type]||'dot-start'}">${ICONS[a.type]||'?'}</div>
      <div class="alert-body">
        <div class="alert-title">${a.title}</div>
        <div class="alert-detail">${a.detail}</div>
      </div>
      <div class="alert-meta">
        <div class="alert-block">⬡ ${a.block}</div>
      </div>
    </div>`).join('');
}

function renderHighPriority(alerts) {
  const high = alerts.filter(a => a.type === 'drain' || a.type === 'approval');
  document.getElementById('highCount').textContent = high.length;
  const feed = document.getElementById('highFeed');
  if (!high.length) {
    feed.innerHTML = `<div class="empty-state" style="padding:2rem 1rem;"><div class="empty-icon" style="font-size:1.5rem;">🔍</div><div class="empty-text">No high-priority alerts</div></div>`;
    return;
  }
  feed.innerHTML = high.map(a => `
    <div class="activity-item">
      <div class="alert-dot ${DOT_CLASS[a.type]}" style="width:28px;height:28px;font-size:11px;">${ICONS[a.type]}</div>
      <div class="activity-line">
        <div class="activity-title">${a.title}</div>
        <div class="activity-addr">${a.detail}</div>
        <div class="activity-block">block ${a.block}</div>
      </div>
    </div>`).join('');
}

async function refresh() {
  try {
    const r = await fetch('/api/data');
    const d = await r.json();

    document.getElementById('sTokens').textContent = d.stats.tokens;
    document.getElementById('sTransfers').textContent = d.stats.transfers.toLocaleString();
    document.getElementById('sDrains').textContent = d.stats.drains;
    document.getElementById('sApprovals').textContent = d.stats.approvals;

    const latestBlock = d.alerts.length ? d.alerts[0].block : '—';
    document.getElementById('blockBadge').textContent = `block ${latestBlock}`;
    document.getElementById('lastUpdate').textContent = `Last update: ${new Date().toLocaleTimeString()}`;

    allAlerts = d.alerts;
    renderFeed();
    renderHighPriority(d.alerts);
  } catch(e) { console.log(e); }
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

@app.route("/api/alert", methods=["POST"])
def add_alert():
    data = load()
    alert = request.json
    data["alerts"].insert(0, alert)
    data["alerts"] = data["alerts"][:100]
    t = alert.get("type","")
    if t == "token": data["stats"]["tokens"] += 1
    elif t == "drain": data["stats"]["drains"] += 1
    elif t == "approval": data["stats"]["approvals"] += 1
    elif t == "transfer": data["stats"]["transfers"] += 1
    save(data)
    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)