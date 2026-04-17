import json
import os
import threading
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS
from web3 import Web3

load_dotenv()

app = Flask(__name__)
CORS(app)

EVENTS_FILE = "/tmp/events.json"
DATA_LOCK = threading.Lock()
MONITOR_STARTED = False

RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")
DRAIN_THRESHOLD = float(os.getenv("DRAIN_THRESHOLD", "100000"))
START_BLOCK = os.getenv("START_BLOCK", "latest")

TRANSFER_TOPIC = Web3.keccak(text="Transfer(address,address,uint256)").hex()
APPROVAL_TOPIC = Web3.keccak(text="Approval(address,address,uint256)").hex()
MAX_UINT256 = 2**256 - 1

TOKEN_CACHE = {}

ERC20_ABI = [
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def default_data():
    return {
        "alerts": [],
        "stats": {"tokens": 0, "transfers": 0, "drains": 0, "approvals": 0},
        "meta": {"status": "starting", "latest_block": None, "last_update": None},
    }


def load_data():
    try:
        with open(EVENTS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return default_data()


def save_data(data):
    with open(EVENTS_FILE, "w") as f:
        json.dump(data, f)


def set_meta(status=None, latest_block=None):
    with DATA_LOCK:
        data = load_data()
        if status is not None:
            data["meta"]["status"] = status
        if latest_block is not None:
            data["meta"]["latest_block"] = latest_block
        data["meta"]["last_update"] = int(time.time())
        save_data(data)


def recompute_token_count(alerts):
    contracts = set()
    for alert in alerts:
        detail = alert.get("detail", "")
        if "|" in detail:
            contract = detail.split("|")[-1].strip()
            if contract.startswith("0x"):
                contracts.add(contract)
    return len(contracts)


def add_alert(alert):
    with DATA_LOCK:
        data = load_data()
        data["alerts"].insert(0, alert)
        data["alerts"] = data["alerts"][:500]

        alert_type = alert.get("type", "")
        if alert_type == "transfer":
            data["stats"]["transfers"] += 1
        elif alert_type == "drain":
            data["stats"]["drains"] += 1
        elif alert_type == "approval":
            data["stats"]["approvals"] += 1

        data["stats"]["tokens"] = recompute_token_count(data["alerts"])
        data["meta"]["latest_block"] = alert.get("block")
        data["meta"]["last_update"] = int(time.time())
        data["meta"]["status"] = "running"
        save_data(data)


def get_token_info(w3, address):
    if address in TOKEN_CACHE:
        return TOKEN_CACHE[address]

    try:
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(address),
            abi=ERC20_ABI,
        )
        symbol = contract.functions.symbol().call()
        decimals = contract.functions.decimals().call()
        TOKEN_CACHE[address] = (symbol, decimals)
        return symbol, decimals
    except Exception:
        TOKEN_CACHE[address] = ("???", 18)
        return "???", 18


def monitor_loop():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))

    if not w3.is_connected():
        print(f"Cannot connect to RPC_URL: {RPC_URL}")
        set_meta(status="rpc_error")
        return

    current = w3.eth.block_number if START_BLOCK == "latest" else int(START_BLOCK)

    print("=================================")
    print("  ERC-20 Mainnet Security Monitor")
    print("=================================")
    print(f"RPC_URL: {RPC_URL}")
    print(f"START_BLOCK: {current}")
    print(f"DRAIN_THRESHOLD: {DRAIN_THRESHOLD:,.0f}")
    print("-" * 50)

    add_alert({
        "type": "start",
        "title": "Monitor Started",
        "detail": f"Ethereum Mainnet | from block {current}",
        "block": current,
    })

    while True:
        try:
            latest = w3.eth.block_number
            if current > latest:
                set_meta(status="running", latest_block=latest)
                time.sleep(2)
                continue

            logs = w3.eth.get_logs({
                "fromBlock": current,
                "toBlock": current,
                "topics": [[TRANSFER_TOPIC, APPROVAL_TOPIC]],
            })

            print(f"Scanning block {current} | logs={len(logs)}")
            set_meta(status="running", latest_block=current)

            for log in logs:
                topic0 = log["topics"][0].hex()
                contract = log["address"]

                if topic0 == TRANSFER_TOPIC and len(log["topics"]) >= 3:
                    symbol, decimals = get_token_info(w3, contract)
                    raw_amount = int(log["data"].hex(), 16) if log["data"] else 0
                    amount = raw_amount / (10 ** decimals)
                    from_addr = "0x" + log["topics"][1].hex()[-40:]
                    to_addr = "0x" + log["topics"][2].hex()[-40:]

                    add_alert({
                        "type": "transfer",
                        "title": f"{symbol} Transfer: {amount:,.2f} tokens",
                        "detail": f"{from_addr} → {to_addr} | {contract}",
                        "block": current,
                    })

                    if amount >= DRAIN_THRESHOLD:
                        add_alert({
                            "type": "drain",
                            "title": f"DRAIN: {amount:,.0f} {symbol}",
                            "detail": f"{from_addr} → {to_addr} | {contract}",
                            "block": current,
                        })

                elif topic0 == APPROVAL_TOPIC and len(log["topics"]) >= 3:
                    symbol, _ = get_token_info(w3, contract)
                    raw_amount = int(log["data"].hex(), 16) if log["data"] else 0

                    if raw_amount == MAX_UINT256:
                        owner = "0x" + log["topics"][1].hex()[-40:]
                        spender = "0x" + log["topics"][2].hex()[-40:]

                        add_alert({
                            "type": "approval",
                            "title": f"Unlimited Approval: {symbol}",
                            "detail": f"{owner} → {spender} | {contract}",
                            "block": current,
                        })

            current += 1
            time.sleep(0.4)

        except Exception as e:
            print(f"Monitor error on block {current}: {e}")
            set_meta(status="error", latest_block=current)
            time.sleep(3)


def start_monitor_once():
    global MONITOR_STARTED
    if MONITOR_STARTED:
        return
    MONITOR_STARTED = True
    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()


HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ERC-20 Security Monitor</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#f3f7fc;
  --bgSoft:#f8fbff;
  --surface:#ffffff;
  --surfaceSoft:#f4f8fc;
  --surfaceAlt:#eef4fb;
  --border:#d7e1ed;
  --borderStrong:#c2d1e3;
  --text:#0f172a;
  --textSoft:#4d6077;
  --textDim:#7e92aa;
  --blue:#0b6bcb;
  --blueDeep:#0f3d75;
  --blueSoft:#e8f2ff;
  --green:#16794b;
  --greenSoft:#e9f7ef;
  --red:#c62828;
  --redSoft:#feeeee;
  --amber:#a96500;
  --amberSoft:#fff4dd;
  --purple:#5d3fd3;
  --purpleSoft:#f1edff;
  --shadowLg:0 18px 48px rgba(15,23,42,.08);
  --shadowMd:0 10px 24px rgba(15,23,42,.06);
  --shadowSm:0 6px 14px rgba(15,23,42,.05);
  --mono:'IBM Plex Mono',monospace;
  --sans:'IBM Plex Sans',sans-serif;
}
html,body{height:100%}
body{
  font-family:var(--sans);
  background:
    radial-gradient(circle at top right, rgba(11,107,203,.06), transparent 22%),
    linear-gradient(180deg,#f9fbff 0%,var(--bg) 100%);
  color:var(--text);
  min-height:100vh;
  font-size:15px;
}
.header{
  position:sticky;top:0;z-index:40;
  display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;
  padding:18px 24px;
  background:rgba(255,255,255,.92);
  backdrop-filter:blur(14px);
  border-bottom:1px solid var(--border);
}
.brand{display:flex;align-items:center;gap:14px}
.brand-badge{
  width:46px;height:46px;border-radius:14px;
  display:flex;align-items:center;justify-content:center;
  background:linear-gradient(135deg,var(--blue),var(--blueDeep));
  color:#fff;font-size:19px;
  box-shadow:0 14px 28px rgba(11,107,203,.22);
}
.brand-title{font-size:23px;font-weight:700;letter-spacing:-.03em}
.brand-sub{
  margin-top:2px;
  font:12px var(--mono);
  color:var(--textDim);
  text-transform:uppercase;
  letter-spacing:.08em;
}
.header-right{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.pill{
  display:inline-flex;align-items:center;gap:8px;
  padding:7px 12px;border-radius:999px;
  border:1px solid var(--borderStrong);
  background:#fff;
  font:600 12px var(--mono);
}
.pill.live{background:var(--greenSoft);border-color:#cde8d7;color:var(--green)}
.pill.block{background:var(--blueSoft);border-color:#d0e0f7;color:var(--blue)}
.pulse{
  width:8px;height:8px;border-radius:50%;background:var(--green);
  animation:pulse 2s infinite;
}
@keyframes pulse{0%,100%{opacity:1;box-shadow:0 0 0 0 rgba(22,121,75,.28)}70%{opacity:.7;box-shadow:0 0 0 8px transparent}}
.page{padding:18px 24px 96px}
.top-info{
  display:flex;gap:12px;flex-wrap:wrap;
  margin-bottom:16px;
  font:13px var(--mono);
  color:var(--textSoft);
}
.surface{
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:20px;
  box-shadow:var(--shadowLg);
}
.controlbar{
  padding:16px 18px;
  display:flex;flex-direction:column;gap:14px;
  margin-bottom:16px;
}
.control-row{
  display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;
}
.seg{
  display:inline-flex;
  padding:4px;
  gap:4px;
  border:1px solid var(--border);
  background:var(--surfaceSoft);
  border-radius:16px;
}
.seg button{
  border:0;background:transparent;color:var(--textSoft);
  padding:10px 14px;border-radius:12px;
  font:600 13px var(--mono);
  cursor:pointer;
}
.seg button.active{
  background:#fff;color:var(--blueDeep);
  box-shadow:var(--shadowSm);
}
.action-group{display:flex;gap:8px;flex-wrap:wrap}
.btn{
  border:1px solid var(--borderStrong);
  background:#fff;color:var(--text);
  border-radius:14px;
  padding:10px 14px;
  font:600 13px var(--mono);
  cursor:pointer;
  transition:.15s ease;
  box-shadow:0 1px 0 rgba(255,255,255,.7) inset;
}
.btn:hover{transform:translateY(-1px)}
.btn.primary{background:linear-gradient(180deg,var(--blue) 0%,#095cad 100%);border-color:var(--blue);color:#fff}
.btn.soft{background:var(--surfaceSoft)}
.btn.danger{color:var(--red);border-color:#efcaca;background:#fff}
.btn.good{color:var(--green);border-color:#cde8d7;background:var(--greenSoft)}
.filters{
  display:grid;grid-template-columns:1.5fr repeat(4, minmax(120px, 1fr));gap:10px;
}
@media(max-width:1100px){.filters{grid-template-columns:1fr 1fr}}
@media(max-width:680px){.filters{grid-template-columns:1fr}}
.input,.select{
  width:100%;
  border:1px solid var(--borderStrong);
  background:#fff;
  color:var(--text);
  border-radius:14px;
  padding:12px 13px;
  font:14px var(--mono);
  outline:none;
}
.input:focus,.select:focus{border-color:var(--blue);box-shadow:0 0 0 4px rgba(11,107,203,.10)}
.metrics{
  display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:16px;
}
@media(max-width:1100px){.metrics{grid-template-columns:repeat(3,1fr)}}
@media(max-width:700px){.metrics{grid-template-columns:repeat(2,1fr)}}
.metric{
  padding:18px;border-radius:18px;background:var(--surface);border:1px solid var(--border);box-shadow:var(--shadowMd);position:relative;overflow:hidden;
}
.metric:before{
  content:'';position:absolute;top:0;left:0;right:0;height:4px;
}
.metric.blue:before{background:var(--blue)}
.metric.green:before{background:var(--green)}
.metric.red:before{background:var(--red)}
.metric.amber:before{background:var(--amber)}
.metric.purple:before{background:var(--purple)}
.metric-label{font:11px var(--mono);text-transform:uppercase;letter-spacing:.08em;color:var(--textDim);margin-bottom:10px}
.metric-value{font-size:34px;font-weight:700;letter-spacing:-.03em}
.metric-sub{margin-top:6px;font-size:12px;color:var(--textSoft)}
.layout{
  display:grid;grid-template-columns:1.65fr 1fr;gap:14px;
}
@media(max-width:1100px){.layout{grid-template-columns:1fr}}
.panel{
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:20px;
  box-shadow:var(--shadowLg);
  overflow:hidden;
}
.panel-head{
  padding:16px 18px;
  border-bottom:1px solid var(--border);
  display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;
  background:linear-gradient(180deg,#fff 0%,#fbfdff 100%);
}
.panel-title{font-size:17px;font-weight:700;letter-spacing:-.02em}
.panel-body{padding:16px 18px}
.feed-tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px}
.feed-tab{
  border:1px solid var(--border);
  background:#fff;color:var(--textSoft);
  border-radius:12px;padding:8px 12px;
  font:700 12px var(--mono);
  cursor:pointer;
}
.feed-tab.active{background:var(--blueDeep);border-color:var(--blueDeep);color:#fff}
.alert{
  padding:14px 0;border-bottom:1px solid var(--border);
}
.alert:last-child{border-bottom:none}
.alert-top{
  display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:7px;
}
.badge{
  display:inline-flex;align-items:center;
  padding:4px 8px;border-radius:999px;
  font:700 10px var(--mono);letter-spacing:.08em;
  border:1px solid transparent;
}
.badge.transfer{background:var(--blueSoft);color:var(--blue);border-color:#d0e0f7}
.badge.drain{background:var(--redSoft);color:var(--red);border-color:#f0caca}
.badge.approval{background:var(--amberSoft);color:var(--amber);border-color:#f0ddb2}
.badge.start{background:var(--greenSoft);color:var(--green);border-color:#cde8d7}
.alert-meta{font:12px var(--mono);color:var(--textDim)}
.alert-title{font-size:15px;font-weight:700;line-height:1.4}
.alert-detail{margin-top:6px;font-size:14px;color:var(--textSoft);line-height:1.55;word-break:break-word}
.split{
  display:grid;gap:14px;
}
.stack{display:grid;gap:14px}
.statline{
  display:flex;justify-content:space-between;align-items:center;gap:10px;
  padding:11px 0;border-bottom:1px solid var(--border);
}
.statline:last-child{border-bottom:none}
.small{font:12px var(--mono);color:var(--textDim)}
.watch-item{
  display:flex;justify-content:space-between;align-items:center;gap:10px;
  padding:10px 0;border-bottom:1px solid var(--border);
}
.watch-item:last-child{border-bottom:none}
.watch-main{min-width:0}
.watch-name{font-size:14px;font-weight:700}
.drawer{
  display:grid;gap:12px;
}
.section-label{
  font:11px var(--mono);text-transform:uppercase;letter-spacing:.08em;color:var(--textDim)
}
.toggle-row{
  display:flex;justify-content:space-between;align-items:center;gap:12px;
  padding:10px 0;border-bottom:1px solid var(--border);
}
.toggle-row:last-child{border-bottom:none}
.toggle{
  width:42px;height:24px;border-radius:999px;background:#d4deea;position:relative;cursor:pointer;
}
.toggle:after{
  content:'';position:absolute;top:3px;left:3px;width:18px;height:18px;border-radius:50%;background:#fff;box-shadow:var(--shadowSm);transition:.18s ease;
}
.toggle.on{background:var(--green)}
.toggle.on:after{transform:translateX(18px)}
.empty{
  padding:28px 0;text-align:center;color:var(--textDim);
}
.footer{
  position:fixed;bottom:0;left:0;right:0;z-index:30;
  background:rgba(255,255,255,.94);backdrop-filter:blur(12px);
  border-top:1px solid var(--border);
  padding:10px 24px;
  display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;
  font:12px var(--mono);color:var(--textDim);
}
.mode-compact .metrics{grid-template-columns:repeat(3,1fr)}
.mode-compact .stack .panel:nth-child(n+3){display:none}
.mode-compact .controlbar{padding:12px 14px}
.mode-executive .filters,.mode-executive .drawer,.mode-executive #watchPanel{display:none}
.mode-executive .layout{grid-template-columns:1fr}
.mode-executive .metrics{grid-template-columns:repeat(4,1fr)}
.mode-investigation .layout{grid-template-columns:1.4fr 1fr}
.mode-investigation #inspectorPanel{order:-1}
</style>
</head>
<body>
<div class="header">
  <div class="brand">
    <div class="brand-badge">🛡</div>
    <div>
      <div class="brand-title">ERC-20 Security Monitor</div>
      <div class="brand-sub">Mainnet Risk Operations Console</div>
    </div>
  </div>
  <div class="header-right">
    <div class="pill live"><span class="pulse"></span><span id="statusPill">RUNNING</span></div>
    <div class="pill block" id="blockPill">Block —</div>
    <button class="btn soft" onclick="refreshNow()">Refresh</button>
    <button class="btn danger" onclick="clearAlerts()">Clear</button>
    <button class="btn primary" onclick="exportAlerts()">Export JSON</button>
  </div>
</div>

<div class="page" id="pageRoot">
  <div class="top-info">
    <div>Chain: <strong>Ethereum Mainnet</strong></div>
    <div>Runtime: <strong id="runtimeStatusTop">—</strong></div>
    <div>Last update: <strong id="lastUpdateTop">—</strong></div>
    <div>Threshold: <strong id="thresholdTop">100,000</strong></div>
  </div>

  <div class="surface controlbar">
    <div class="control-row">
      <div class="seg" id="modeSeg">
        <button class="active" data-mode="live" onclick="setMode('live', this)">Live</button>
        <button data-mode="investigation" onclick="setMode('investigation', this)">Investigation</button>
        <button data-mode="compact" onclick="setMode('compact', this)">Compact</button>
        <button data-mode="executive" onclick="setMode('executive', this)">Executive</button>
      </div>
      <div class="action-group">
        <button class="btn soft" onclick="toggleDrawer()">Advanced Options</button>
        <button class="btn good" onclick="setThresholdPreset(100000)">Threshold 100k</button>
        <button class="btn soft" onclick="setThresholdPreset(500000)">Threshold 500k</button>
        <button class="btn soft" onclick="setThresholdPreset(1000000)">Threshold 1M</button>
      </div>
    </div>

    <div class="filters">
      <input class="input" id="searchBox" placeholder="Search token, address, contract..." oninput="renderAll()">
      <select class="select" id="severityFilter" onchange="renderAll()">
        <option value="all">Severity: All</option>
        <option value="critical">Critical Only</option>
        <option value="high">High + Critical</option>
        <option value="info">Info Only</option>
      </select>
      <select class="select" id="typeFilter" onchange="renderAll()">
        <option value="all">Type: All</option>
        <option value="transfer">Transfers</option>
        <option value="drain">Drains</option>
        <option value="approval">Approvals</option>
        <option value="start">System</option>
      </select>
      <select class="select" id="sortFilter" onchange="renderAll()">
        <option value="newest">Sort: Newest first</option>
        <option value="oldest">Sort: Oldest first</option>
      </select>
      <select class="select" id="watchOnlyFilter" onchange="renderAll()">
        <option value="all">Scope: All alerts</option>
        <option value="watched">Watched only</option>
      </select>
    </div>

    <div class="drawer" id="advancedDrawer" style="display:none">
      <div class="section-label">Advanced Controls</div>
      <div class="filters">
        <input class="input" id="thresholdInput" type="number" value="100000" placeholder="Drain threshold">
        <select class="select" id="refreshMode">
          <option>Refresh every 5s</option>
          <option>Refresh every 10s</option>
          <option>Refresh every 15s</option>
        </select>
        <select class="select" id="layoutDensity">
          <option>Density: Comfortable</option>
          <option>Density: Compact</option>
        </select>
        <select class="select" id="focusToken">
          <option value="">Focus token: Any</option>
        </select>
        <select class="select" id="blockWindow">
          <option>Window: Live</option>
          <option>Window: Last 100 alerts</option>
          <option>Window: Last 250 alerts</option>
        </select>
      </div>

      <div class="section-label">Feature Toggles</div>
      <div class="split">
        <div class="toggle-row"><span>Show priority queue</span><div class="toggle on" onclick="this.classList.toggle('on')"></div></div>
        <div class="toggle-row"><span>Show runtime inspector</span><div class="toggle on" onclick="this.classList.toggle('on')"></div></div>
        <div class="toggle-row"><span>Highlight critical alerts</span><div class="toggle on" onclick="this.classList.toggle('on')"></div></div>
        <div class="toggle-row"><span>Watched wallet emphasis</span><div class="toggle on" onclick="this.classList.toggle('on')"></div></div>
      </div>
    </div>
  </div>

  <div class="metrics">
    <div class="metric blue"><div class="metric-label">Tokens Tracked</div><div class="metric-value" id="sTokens">0</div><div class="metric-sub">Unique ERC-20 contracts observed</div></div>
    <div class="metric green"><div class="metric-label">Transfers Scanned</div><div class="metric-value" id="sTransfers">0</div><div class="metric-sub">Processed transfer events</div></div>
    <div class="metric red"><div class="metric-label">Drain Alerts</div><div class="metric-value" id="sDrains">0</div><div class="metric-sub">Threshold exceeded</div></div>
    <div class="metric amber"><div class="metric-label">Unlimited Approvals</div><div class="metric-value" id="sApprovals">0</div><div class="metric-sub">MAX_UINT256 approvals</div></div>
    <div class="metric purple"><div class="metric-label">Priority Queue</div><div class="metric-value" id="sPriority">0</div><div class="metric-sub">Critical incidents requiring attention</div></div>
  </div>

  <div class="layout">
    <div class="panel">
      <div class="panel-head">
        <div class="panel-title">Live Alert Feed</div>
        <div class="small" id="feedCount">0 events</div>
      </div>
      <div class="panel-body">
        <div class="feed-tabs">
          <button class="feed-tab active" onclick="setFeedTab('all', this)">All</button>
          <button class="feed-tab" onclick="setFeedTab('transfer', this)">Transfers</button>
          <button class="feed-tab" onclick="setFeedTab('drain', this)">Drains</button>
          <button class="feed-tab" onclick="setFeedTab('approval', this)">Approvals</button>
          <button class="feed-tab" onclick="setFeedTab('start', this)">System</button>
        </div>
        <div id="alertList" class="empty">Waiting for alerts...</div>
      </div>
    </div>

    <div class="stack">
      <div class="panel" id="priorityPanel">
        <div class="panel-head">
          <div class="panel-title">Priority Queue</div>
          <div class="small" id="priorityCount">0</div>
        </div>
        <div class="panel-body" id="priorityList">
          <div class="empty">No critical alerts</div>
        </div>
      </div>

      <div class="panel" id="inspectorPanel">
        <div class="panel-head">
          <div class="panel-title">Runtime Inspector</div>
          <div class="small">Live</div>
        </div>
        <div class="panel-body">
          <div class="statline"><span>Status</span><strong id="runtimeStatus">—</strong></div>
          <div class="statline"><span>Latest block</span><strong id="runtimeBlock">—</strong></div>
          <div class="statline"><span>Last sync</span><strong id="runtimeSync">—</strong></div>
          <div class="statline"><span>Poll model</span><strong>On-chain logs</strong></div>
        </div>
      </div>

      <div class="panel" id="watchPanel">
        <div class="panel-head">
          <div class="panel-title">Watchlist</div>
          <button class="btn soft" onclick="clearWatch()">Clear</button>
        </div>
        <div class="panel-body">
          <div style="display:grid;gap:10px">
            <input class="input" id="watchInput" placeholder="0x... full address">
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              <button class="btn primary" onclick="addWatch()">Add Watch</button>
              <button class="btn soft" onclick="pasteAddr()">Paste</button>
            </div>
          </div>
          <div id="watchList" style="margin-top:14px">
            <div class="empty">No watched addresses</div>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-head">
          <div class="panel-title">Selected Alert</div>
          <div class="small">Inspector</div>
        </div>
        <div class="panel-body" id="selectedAlert">
          <div class="empty">Select or search alerts to inspect activity context</div>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="footer">
  <div>Monitor source: Ethereum event logs</div>
  <div id="footerTime">Last sync: —</div>
</div>

<script>
let allAlerts = [];
let watchlist = [];
let feedTab = 'all';
let currentMode = 'live';
let selectedAlert = null;

function escapeHtml(str){
  return (str || '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
}
function short(addr){
  return addr && addr.length > 12 ? addr.slice(0,6) + '…' + addr.slice(-4) : (addr || '—');
}
function parseDetail(detail){
  detail = detail || '';
  const arrow = detail.indexOf('→');
  const pipe = detail.indexOf('|');
  const from = arrow > -1 ? detail.substring(0, arrow).trim() : '';
  const to = pipe > -1 ? detail.substring(arrow + 1, pipe).trim() : '';
  const contract = pipe > -1 ? detail.substring(pipe + 1).trim() : '';
  return { from, to, contract };
}
function severityFor(alert){
  if (alert.type === 'drain') return 'critical';
  if (alert.type === 'approval') return 'high';
  if (alert.type === 'transfer') return 'info';
  return 'info';
}
function matchesWatch(alert){
  if (!watchlist.length) return false;
  const p = parseDetail(alert.detail || '');
  const text = ((p.from || '') + ' ' + (p.to || '') + ' ' + (p.contract || '')).toLowerCase();
  return watchlist.some(w => text.includes(w.addr.toLowerCase()));
}
function filteredAlerts(){
  const search = (document.getElementById('searchBox')?.value || '').toLowerCase().trim();
  const severity = document.getElementById('severityFilter')?.value || 'all';
  const type = document.getElementById('typeFilter')?.value || 'all';
  const sort = document.getElementById('sortFilter')?.value || 'newest';
  const watchOnly = document.getElementById('watchOnlyFilter')?.value || 'all';
  const focusToken = document.getElementById('focusToken')?.value || '';

  let list = [...allAlerts];

  if (feedTab !== 'all') list = list.filter(a => a.type === feedTab);
  if (type !== 'all') list = list.filter(a => a.type === type);

  if (severity === 'critical') list = list.filter(a => severityFor(a) === 'critical');
  if (severity === 'high') list = list.filter(a => ['critical','high'].includes(severityFor(a)));
  if (severity === 'info') list = list.filter(a => severityFor(a) === 'info');

  if (watchOnly === 'watched') list = list.filter(matchesWatch);

  if (focusToken) list = list.filter(a => (a.title || '').toLowerCase().includes(focusToken.toLowerCase()));

  if (search) {
    list = list.filter(a => ((a.title || '') + ' ' + (a.detail || '')).toLowerCase().includes(search));
  }

  if (sort === 'oldest') list.reverse();
  return list;
}
function setMode(mode, el){
  currentMode = mode;
  document.querySelectorAll('#modeSeg button').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  const root = document.getElementById('pageRoot');
  root.classList.remove('mode-live','mode-investigation','mode-compact','mode-executive');
  root.classList.add('mode-' + mode);
}
function setFeedTab(mode, el){
  feedTab = mode;
  document.querySelectorAll('.feed-tab').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  renderAll();
}
function toggleDrawer(){
  const el = document.getElementById('advancedDrawer');
  el.style.display = el.style.display === 'none' ? 'grid' : 'none';
}
function setThresholdPreset(value){
  document.getElementById('thresholdInput').value = value;
  document.getElementById('thresholdTop').textContent = Number(value).toLocaleString();
}
function selectAlert(index){
  const list = filteredAlerts();
  selectedAlert = list[index] || null;
  renderSelected();
}
function renderSelected(){
  const box = document.getElementById('selectedAlert');
  if (!selectedAlert){
    box.innerHTML = '<div class="empty">Select or search alerts to inspect activity context</div>';
    return;
  }
  const p = parseDetail(selectedAlert.detail || '');
  box.innerHTML = `
    <div class="drawer">
      <div><span class="badge ${escapeHtml(selectedAlert.type)}">${escapeHtml((selectedAlert.type || '').toUpperCase())}</span></div>
      <div style="font-size:16px;font-weight:700">${escapeHtml(selectedAlert.title || 'Alert')}</div>
      <div class="statline"><span>Block</span><strong>${escapeHtml(String(selectedAlert.block || '—'))}</strong></div>
      <div class="statline"><span>Severity</span><strong>${escapeHtml(severityFor(selectedAlert).toUpperCase())}</strong></div>
      <div class="section-label">Addresses</div>
      <div class="small">From: ${escapeHtml(p.from || '—')}</div>
      <div class="small">To: ${escapeHtml(p.to || '—')}</div>
      <div class="small">Contract: ${escapeHtml(p.contract || '—')}</div>
    </div>
  `;
}
function renderAlerts(){
  const list = filteredAlerts();
  document.getElementById('feedCount').textContent = list.length + ' events';

  if (!list.length){
    document.getElementById('alertList').innerHTML = '<div class="empty">No alerts match the current filters</div>';
    return;
  }

  document.getElementById('alertList').innerHTML = list.slice(0, 120).map((a, i) => {
    const p = parseDetail(a.detail || '');
    const watched = matchesWatch(a);
    return `
      <div class="alert" onclick="selectAlert(${i})" style="cursor:pointer;${watched ? 'background:linear-gradient(180deg,#fbfdff 0%,#f3f8ff 100%);padding-left:8px;padding-right:8px;border-radius:12px;' : ''}">
        <div class="alert-top">
          <span class="badge ${escapeHtml(a.type)}">${escapeHtml((a.type || '').toUpperCase())}</span>
          <span class="alert-meta">#${escapeHtml(String(a.block || '—'))}</span>
        </div>
        <div class="alert-title">${escapeHtml(a.title || 'Alert')}</div>
        <div class="alert-detail">
          ${p.contract
            ? `<div><strong>From:</strong> ${escapeHtml(short(p.from))} <strong>To:</strong> ${escapeHtml(short(p.to))}</div><div><strong>Contract:</strong> ${escapeHtml(short(p.contract))}</div>`
            : escapeHtml(a.detail || '')}
          ${watched ? '<div style="margin-top:6px;color:var(--blue);font-weight:700">Watched address match</div>' : ''}
        </div>
      </div>
    `;
  }).join('');
}
function renderPriority(){
  const priority = allAlerts.filter(a => ['drain','approval'].includes(a.type));
  document.getElementById('priorityCount').textContent = priority.length;
  document.getElementById('sPriority').textContent = priority.length.toLocaleString();

  if (!priority.length){
    document.getElementById('priorityList').innerHTML = '<div class="empty">No critical alerts</div>';
    return;
  }

  document.getElementById('priorityList').innerHTML = priority.slice(0, 8).map(a => `
    <div class="statline">
      <div>
        <div style="font-size:14px;font-weight:700">${escapeHtml(a.title || 'Alert')}</div>
        <div class="small" style="margin-top:4px">Block ${escapeHtml(String(a.block || '—'))}</div>
      </div>
      <span class="badge ${escapeHtml(a.type)}">${escapeHtml(a.type.toUpperCase())}</span>
    </div>
  `).join('');
}
function refreshFocusTokenOptions(){
  const sel = document.getElementById('focusToken');
  const current = sel.value;
  const tokens = [...new Set(allAlerts.map(a => {
    const m = (a.title || '').match(/([A-Z0-9]{2,10})/);
    return m ? m[1] : '';
  }).filter(Boolean))].slice(0, 50);

  sel.innerHTML = '<option value="">Focus token: Any</option>' + tokens.map(t => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('');
  sel.value = current;
}
function renderWatch(){
  const box = document.getElementById('watchList');
  if (!watchlist.length){
    box.innerHTML = '<div class="empty">No watched addresses</div>';
    return;
  }
  box.innerHTML = watchlist.map((w, i) => `
    <div class="watch-item">
      <div class="watch-main">
        <div class="watch-name">${escapeHtml(w.label)}</div>
        <div class="small">${escapeHtml(short(w.addr))}</div>
      </div>
      <button class="btn soft" onclick="removeWatch(${i})">Remove</button>
    </div>
  `).join('');
}
function addWatch(){
  const value = document.getElementById('watchInput').value.trim();
  if (!value || value.length !== 42 || !value.startsWith('0x')){
    alert('Enter a valid 0x address');
    return;
  }
  watchlist.push({ addr: value, label: 'Watch ' + (watchlist.length + 1) });
  document.getElementById('watchInput').value = '';
  renderAll();
}
function removeWatch(i){
  watchlist.splice(i, 1);
  renderAll();
}
function clearWatch(){
  watchlist = [];
  renderAll();
}
function pasteAddr(){
  navigator.clipboard.readText().then(t => {
    document.getElementById('watchInput').value = t.trim();
  }).catch(() => {});
}
async function clearAlerts(){
  if (!confirm('Clear all alerts?')) return;
  await fetch('/api/clear', { method: 'POST' });
  selectedAlert = null;
  await refreshNow();
}
function exportAlerts(){
  const blob = new Blob([JSON.stringify(allAlerts, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'erc20-alerts.json';
  a.click();
}
function renderAll(){
  renderAlerts();
  renderPriority();
  renderWatch();
  renderSelected();
}
async function refreshNow(){
  try{
    const res = await fetch('/api/data');
    const data = await res.json();
    allAlerts = data.alerts || [];
    const stats = data.stats || {};
    const meta = data.meta || {};

    document.getElementById('sTokens').textContent = (stats.tokens || 0).toLocaleString();
    document.getElementById('sTransfers').textContent = (stats.transfers || 0).toLocaleString();
    document.getElementById('sDrains').textContent = (stats.drains || 0).toLocaleString();
    document.getElementById('sApprovals').textContent = (stats.approvals || 0).toLocaleString();

    document.getElementById('blockPill').textContent = 'Block ' + (meta.latest_block ?? '—');
    document.getElementById('runtimeBlock').textContent = meta.latest_block ?? '—';
    document.getElementById('runtimeStatus').textContent = meta.status || '—';
    document.getElementById('runtimeStatusTop').textContent = meta.status || '—';
    document.getElementById('statusPill').textContent = (meta.status || 'unknown').toUpperCase();

    const now = new Date().toLocaleTimeString();
    document.getElementById('lastUpdateTop').textContent = now;
    document.getElementById('runtimeSync').textContent = now;
    document.getElementById('footerTime').textContent = 'Last sync: ' + now;

    refreshFocusTokenOptions();
    renderAll();
  }catch(e){
    console.log(e);
  }
}
refreshNow();
setInterval(refreshNow, 5000);
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/health")
def health():
    return jsonify({"ok": True})


@app.route("/api/data")
def api_data():
    with DATA_LOCK:
        return jsonify(load_data())


@app.route("/api/alert", methods=["POST"])
def api_alert():
    add_alert(request.json or {})
    return jsonify({"ok": True})


@app.route("/api/clear", methods=["POST"])
def api_clear():
    with DATA_LOCK:
        save_data(default_data())
    return jsonify({"ok": True})


if __name__ == "__main__":
    start_monitor_once()
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
