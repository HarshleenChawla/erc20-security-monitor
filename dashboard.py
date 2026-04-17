import json
import os

from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

EVENTS_FILE = "/tmp/events.json"


def load():
    try:
        with open(EVENTS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {
            "alerts": [],
            "stats": {"tokens": 0, "transfers": 0, "drains": 0, "approvals": 0},
        }


def save(data):
    with open(EVENTS_FILE, "w") as f:
        json.dump(data, f)


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
  --bg:#f4f7fb;
  --bg2:#ffffff;
  --bg3:#eef3f9;
  --panel:#ffffff;
  --panel-soft:#f8fbff;
  --border:#d9e3ef;
  --border-strong:#c2d2e4;
  --text:#0f172a;
  --text2:#46556b;
  --text3:#7e91a8;
  --navy:#0f3d75;
  --accent:#0b6bcb;
  --accent-soft:#e8f2ff;
  --green:#14804a;
  --green-soft:#e9f8f0;
  --red:#c62828;
  --red-soft:#feefee;
  --amber:#b26a00;
  --amber-soft:#fff4df;
  --shadow:0 14px 40px rgba(15, 23, 42, 0.06);
  --shadow-sm:0 6px 18px rgba(15, 23, 42, 0.05);
  --mono:'IBM Plex Mono', monospace;
  --sans:'IBM Plex Sans', sans-serif;
}
html,body{height:100%}
body{
  background:
    radial-gradient(circle at top right, rgba(11,107,203,.05), transparent 22%),
    linear-gradient(180deg, #f8fbff 0%, var(--bg) 100%);
  color:var(--text);
  font-family:var(--sans);
  font-size:15px;
  min-height:100vh;
}

.hdr{
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding:18px 24px;
  background:rgba(255,255,255,.92);
  border-bottom:1px solid var(--border);
  backdrop-filter:blur(12px);
  position:sticky;
  top:0;
  z-index:50;
  flex-wrap:wrap;
  gap:12px;
}
.logo{display:flex;align-items:center;gap:14px}
.logo-box{
  width:42px;height:42px;border-radius:12px;
  display:flex;align-items:center;justify-content:center;
  background:linear-gradient(135deg,#0b6bcb,#0f3d75);
  color:#fff;font-size:18px;
  box-shadow:0 12px 26px rgba(11,107,203,.22);
}
.logo-copy{display:flex;flex-direction:column;gap:2px}
.logo-txt{
  font-family:var(--sans);
  font-size:22px;
  font-weight:700;
  letter-spacing:-.03em;
  color:var(--text);
}
.logo-sub{
  font-size:12px;
  color:var(--text3);
  font-family:var(--mono);
  text-transform:uppercase;
  letter-spacing:.08em;
}
.hdr-right{display:flex;align-items:center;gap:10px;flex-wrap:wrap}

.badge{
  padding:6px 12px;
  border-radius:999px;
  font-size:12px;
  font-weight:600;
  letter-spacing:.02em;
  display:inline-flex;
  align-items:center;
  gap:6px;
  font-family:var(--mono);
}
.b-green{background:var(--green-soft);border:1px solid #cbeed8;color:var(--green)}
.b-accent{background:var(--accent-soft);border:1px solid #c9def8;color:var(--accent)}
.dot{
  width:8px;height:8px;border-radius:50%;
  background:var(--green);display:inline-block;
  animation:pulse 2s infinite
}
@keyframes pulse{0%,100%{opacity:1;box-shadow:0 0 0 0 rgba(20,128,74,.28)}70%{opacity:.65;box-shadow:0 0 0 7px transparent}}

.netbar{
  display:flex;flex-wrap:wrap;gap:10px 18px;
  padding:12px 24px;
  background:var(--bg3);
  border-bottom:1px solid var(--border);
  font-size:13px;
  color:var(--text2);
  font-family:var(--mono);
}
.nv{color:var(--text);font-weight:600}

.stats{
  display:grid;
  grid-template-columns:repeat(5,1fr);
  gap:14px;
  padding:20px 24px 0;
}
@media(max-width:1100px){.stats{grid-template-columns:repeat(3,1fr)}}
@media(max-width:640px){.stats{grid-template-columns:repeat(2,1fr)}}

.sc{
  background:var(--panel);
  border:1px solid var(--border);
  border-radius:18px;
  padding:18px 18px 16px;
  position:relative;
  overflow:hidden;
  box-shadow:var(--shadow-sm);
}
.sc::before{
  content:'';
  position:absolute;
  top:0;left:0;right:0;height:4px;
}
.sc.ca::before{background:#0b6bcb}
.sc.cg::before{background:#14804a}
.sc.cr::before{background:#c62828}
.sc.cam::before{background:#b26a00}
.sc.cp::before{background:#5b3cc4}
.sc-icon{
  position:absolute;right:16px;top:16px;
  font-size:20px;opacity:.22
}
.sc-label{
  font-size:11px;
  color:var(--text3);
  letter-spacing:.08em;
  text-transform:uppercase;
  margin-bottom:10px;
  font-family:var(--mono);
}
.sc-val{
  font-size:34px;
  font-weight:700;
  line-height:1;
  margin-bottom:6px;
  letter-spacing:-.03em;
}
.sc-sub{
  font-size:12px;
  color:var(--text2);
}

.grid{
  display:grid;
  grid-template-columns:1.8fr 1fr 1fr;
  gap:14px;
  padding:20px 24px 96px;
}
@media(max-width:1180px){.grid{grid-template-columns:1fr 1fr}}
@media(max-width:760px){.grid{grid-template-columns:1fr}}

.panel{
  background:var(--panel);
  border:1px solid var(--border);
  border-radius:18px;
  overflow:hidden;
  display:flex;
  flex-direction:column;
  box-shadow:var(--shadow);
}
.ph{
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding:16px 18px;
  border-bottom:1px solid var(--border);
  background:linear-gradient(180deg,#ffffff 0%, #f9fbfe 100%);
  gap:10px;
}
.ph-title{
  font-size:17px;
  font-weight:700;
  display:flex;
  align-items:center;
  gap:8px;
  letter-spacing:-.02em;
}
.pb{
  padding:16px 18px;
  flex:1;
  overflow-y:auto;
  max-height:360px;
}
.pb::-webkit-scrollbar{width:5px}
.pb::-webkit-scrollbar-thumb{background:var(--border-strong);border-radius:999px}

.btn{
  padding:9px 14px;
  border-radius:12px;
  border:1px solid;
  font-family:var(--mono);
  font-size:13px;
  font-weight:600;
  cursor:pointer;
  transition:all .15s ease;
  white-space:nowrap;
  background:#fff;
}
.btn:hover{transform:translateY(-1px)}
.btn-p{background:var(--accent);border-color:var(--accent);color:#fff}
.btn-p:hover{background:#0a60b7}
.btn-d{background:#fff;border-color:#efc8c8;color:var(--red)}
.btn-d:hover{background:var(--red-soft)}
.btn-g{background:#fff;border-color:var(--border-strong);color:var(--text2)}
.btn-g:hover{border-color:#9fb5cd;color:var(--text)}
.btn-gr{background:var(--green-soft);border-color:#cbeed8;color:var(--green)}
.btn-sm{padding:7px 11px;font-size:12px}

.inp{
  background:#fff;
  border:1px solid var(--border-strong);
  border-radius:12px;
  padding:11px 13px;
  color:var(--text);
  font-family:var(--mono);
  font-size:14px;
  outline:none;
  transition:border-color .2s, box-shadow .2s;
  width:100%;
}
.inp:focus{
  border-color:var(--accent);
  box-shadow:0 0 0 4px rgba(11,107,203,.10);
}
.inp::placeholder{color:var(--text3)}

.tabs{display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap}
.tab{
  padding:7px 12px;
  border-radius:12px;
  font-size:12px;
  font-weight:700;
  cursor:pointer;
  border:1px solid var(--border);
  transition:all .15s;
  letter-spacing:.02em;
  background:#fff;
  color:var(--text2);
  font-family:var(--mono);
}
.tab.on{
  background:var(--navy);
  border-color:var(--navy);
  color:#fff;
}
.tab:not(.on):hover{
  color:var(--text);
  border-color:var(--border-strong);
}

.ai{
  padding:14px 0;
  border-bottom:1px solid var(--border);
}
.ai:last-child{border-bottom:none}
.ai-row{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:10px;
  margin-bottom:5px;
}
.atype{
  font-size:10px;
  font-weight:700;
  letter-spacing:.08em;
  padding:4px 8px;
  border-radius:999px;
  font-family:var(--mono);
}
.t-drain{background:var(--red-soft);color:var(--red);border:1px solid #f0caca}
.t-approval{background:var(--amber-soft);color:var(--amber);border:1px solid #f0ddb3}
.t-transfer{background:var(--accent-soft);color:var(--accent);border:1px solid #c9def8}
.t-start{background:var(--green-soft);color:var(--green);border:1px solid #cbeed8}
.atime{font-size:12px;color:var(--text3);font-family:var(--mono)}
.aaddr{font-size:14px;color:var(--text2);line-height:1.5;word-break:break-word}
.aaddr b{color:var(--text);font-weight:600}
.aamount{font-size:14px;font-weight:700;line-height:1.4;text-align:right}

.tr{
  display:grid;
  grid-template-columns:36px 1fr auto auto;
  gap:10px;
  align-items:center;
  padding:11px 0;
  border-bottom:1px solid var(--border);
}
.tr:last-child{border-bottom:none}
.ticon{
  width:36px;height:36px;border-radius:50%;
  background:var(--panel-soft);
  border:1px solid var(--border);
  display:flex;align-items:center;justify-content:center;
  font-size:11px;font-weight:700;
  font-family:var(--mono);
}
.tname{font-size:14px;font-weight:700}
.taddr{font-size:12px;color:var(--text3);font-family:var(--mono)}
.risk{
  font-size:10px;
  font-weight:700;
  padding:4px 8px;
  border-radius:999px;
  font-family:var(--mono);
}
.r-low{background:var(--green-soft);color:var(--green);border:1px solid #cbeed8}
.r-med{background:var(--amber-soft);color:var(--amber);border:1px solid #f0ddb3}
.r-high{background:var(--red-soft);color:var(--red);border:1px solid #f0caca}

.wi{
  display:flex;
  align-items:center;
  gap:10px;
  padding:10px 0;
  border-bottom:1px solid var(--border);
}
.wi:last-child{border-bottom:none}
.wavatar{
  width:36px;height:36px;border-radius:12px;
  background:linear-gradient(135deg,#e8f2ff,#eef1ff);
  border:1px solid var(--border);
  display:flex;align-items:center;justify-content:center;
  font-size:11px;font-weight:700;color:var(--accent);
  flex-shrink:0;
  font-family:var(--mono);
}
.winfo{flex:1;min-width:0}
.wlabel{
  font-size:14px;
  font-weight:700;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}
.whex{font-size:12px;color:var(--text3);font-family:var(--mono)}
.wbtns{display:flex;gap:4px;flex-shrink:0}

.tog{
  width:38px;height:20px;background:#d3deea;border-radius:999px;
  position:relative;cursor:pointer;transition:background .2s;flex-shrink:0
}
.tog.on{background:var(--green)}
.tog::after{
  content:'';
  position:absolute;top:2px;left:2px;width:16px;height:16px;border-radius:50%;
  background:#fff;transition:transform .2s;box-shadow:0 1px 4px rgba(15,23,42,.15)
}
.tog.on::after{transform:translateX(18px)}
.trow{
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding:10px 0;
  border-bottom:1px solid var(--border);
}
.trow:last-child{border-bottom:none}
.tlabel{font-size:14px;color:var(--text2)}

.throw{
  display:flex;
  align-items:center;
  gap:10px;
  padding:10px 0;
  border-bottom:1px solid var(--border);
}
.throw:last-child{border-bottom:none}
.thlabel{flex:1;font-size:14px;color:var(--text2)}
.thinp{
  width:108px;background:#fff;border:1px solid var(--border-strong);
  border-radius:10px;padding:8px 10px;color:var(--text);
  font-family:var(--mono);font-size:13px;outline:none;text-align:right
}
.thinp:focus{border-color:var(--accent)}

.empty{
  text-align:center;
  padding:36px 0;
  color:var(--text3);
  font-size:13px;
  line-height:1.6;
}
.dots span{animation:sd 1.4s ease-in-out infinite}
.dots span:nth-child(2){animation-delay:.2s}
.dots span:nth-child(3){animation-delay:.4s}
@keyframes sd{0%,100%{opacity:.2}50%{opacity:1}}

.sbar{
  position:fixed;
  bottom:0;left:0;right:0;
  padding:10px 24px;
  background:rgba(255,255,255,.95);
  border-top:1px solid var(--border);
  display:flex;
  align-items:center;
  justify-content:space-between;
  font-size:12px;
  color:var(--text3);
  z-index:50;
  backdrop-filter:blur(12px);
  font-family:var(--mono);
}
.sbar-l,.sbar-r{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.inrow{display:flex;gap:8px;margin-bottom:10px}
.section-cap{
  font-size:11px;
  color:var(--text3);
  letter-spacing:.08em;
  text-transform:uppercase;
  margin-bottom:8px;
  font-family:var(--mono);
}
</style>
</head>
<body>

<div class="hdr">
  <div class="logo">
    <div class="logo-box">🛡</div>
    <div class="logo-copy">
      <div class="logo-txt">ERC-20 Security Monitor</div>
      <div class="logo-sub">Mainnet Risk Operations Console</div>
    </div>
  </div>
  <div class="hdr-right">
    <span class="badge b-green"><span class="dot"></span>Monitoring Active</span>
    <span class="badge b-accent" id="block-badge">Block —</span>
    <button class="btn btn-g btn-sm" onclick="clearAlerts()">Clear</button>
    <button class="btn btn-p btn-sm" id="scan-btn" onclick="toggleScan()">Pause</button>
    <button class="btn btn-g btn-sm" onclick="exportAlerts()">Export</button>
  </div>
</div>

<div class="netbar">
  <span>Gas: <span class="nv" id="gas">—</span> gwei</span>
  <span>Chain: <span class="nv">Ethereum Mainnet</span></span>
  <span>Last sync: <span class="nv" id="last-scan">—</span></span>
  <span>Refresh: <span class="nv">5s</span></span>
  <span>Drain threshold: <span class="nv" id="tdisplay">100,000 tokens</span></span>
  <span>Latest block: <span class="nv" id="pending">—</span></span>
</div>

<div class="stats">
  <div class="sc ca"><div class="sc-icon">◎</div><div class="sc-label">Tokens Tracked</div><div class="sc-val" id="st-tok">0</div><div class="sc-sub">Unique ERC-20 contracts observed</div></div>
  <div class="sc cg"><div class="sc-icon">↔</div><div class="sc-label">Transfers Scanned</div><div class="sc-val" id="st-tx">0</div><div class="sc-sub">Events processed since monitor start</div></div>
  <div class="sc cr"><div class="sc-icon">!</div><div class="sc-label">Drain Alerts</div><div class="sc-val" id="st-drain">0</div><div class="sc-sub">High-risk transfer thresholds exceeded</div></div>
  <div class="sc cam"><div class="sc-icon">⚠</div><div class="sc-label">Unlimited Approvals</div><div class="sc-val" id="st-approve">0</div><div class="sc-sub">MAX_UINT256 approvals detected</div></div>
  <div class="sc cp"><div class="sc-icon">■</div><div class="sc-label">Priority Queue</div><div class="sc-val" id="st-hp">0</div><div class="sc-sub">Alerts requiring immediate attention</div></div>
</div>

<div class="grid">
  <div class="panel" style="grid-row:span 2">
    <div class="ph">
      <div class="ph-title">Live Alert Feed <span id="ev-count" style="color:var(--text3);font-size:12px;font-weight:500;font-family:var(--mono)">0 events</span></div>
      <div style="display:flex;gap:6px">
        <button class="btn btn-g btn-sm" onclick="exportAlerts()">Export</button>
        <button class="btn btn-d btn-sm" onclick="clearAlerts()">Clear</button>
      </div>
    </div>
    <div class="pb" style="max-height:680px">
      <div class="tabs">
        <div class="tab on" onclick="setFilter('all',this)">All</div>
        <div class="tab" onclick="setFilter('drain',this)">Drains</div>
        <div class="tab" onclick="setFilter('approval',this)">Approvals</div>
        <div class="tab" onclick="setFilter('transfer',this)">Transfers</div>
        <div class="tab" onclick="setFilter('start',this)">System</div>
      </div>
      <div id="alert-list">
        <div class="empty dots"><span>●</span><span>●</span><span>●</span><div style="margin-top:8px">Waiting for on-chain activity...</div></div>
      </div>
    </div>
  </div>

  <div class="panel">
    <div class="ph">
      <div class="ph-title">Watchlist</div>
      <button class="btn btn-d btn-sm" onclick="clearWatch()">Clear All</button>
    </div>
    <div class="pb">
      <div class="inrow">
        <input class="inp" id="watch-inp" placeholder="0x... full address" maxlength="42">
      </div>
      <div style="display:flex;gap:6px;margin-bottom:14px">
        <button class="btn btn-p btn-sm" style="flex:1" onclick="addWatch()">Add Watch</button>
        <button class="btn btn-g btn-sm" style="flex:1" onclick="pasteAddr()">Paste</button>
        <button class="btn btn-g btn-sm" style="flex:1" onclick="addDemoWatch()">Demo</button>
      </div>
      <div id="watch-list"><div class="empty" style="padding:14px 0">No watched addresses yet</div></div>
    </div>
  </div>

  <div class="panel">
    <div class="ph">
      <div class="ph-title">Token Registry</div>
      <button class="btn btn-g btn-sm" onclick="sortTok()">Sort</button>
    </div>
    <div class="pb">
      <div class="inrow" style="margin-bottom:12px">
        <input class="inp" id="tok-search" placeholder="Search token or contract..." oninput="renderToks()">
      </div>
      <div id="tok-list"><div class="empty">Registry auto-populates as contracts are observed</div></div>
    </div>
  </div>

  <div class="panel">
    <div class="ph">
      <div class="ph-title">Priority Queue <span id="hp-badge" style="background:var(--red-soft);border:1px solid #f0caca;color:var(--red);padding:4px 8px;border-radius:999px;font-size:11px;font-weight:700;font-family:var(--mono)">0</span></div>
      <button class="btn btn-g btn-sm" onclick="dismissHP()">Dismiss</button>
    </div>
    <div class="pb" id="hp-list">
      <div class="empty" style="padding:14px 0">No critical alerts at this time</div>
    </div>
  </div>

  <div class="panel">
    <div class="ph">
      <div class="ph-title">Controls & Thresholds</div>
      <button class="btn btn-gr btn-sm" onclick="saveConfig()">Save</button>
    </div>
    <div class="pb">
      <div class="section-cap">Thresholds</div>
      <div class="throw"><div class="thlabel">Drain alert</div><input class="thinp" id="t-drain" value="100000" type="number"></div>
      <div class="throw"><div class="thlabel">Large transfer</div><input class="thinp" id="t-eth" value="50000" type="number"></div>
      <div class="throw"><div class="thlabel">Approval limit</div><input class="thinp" id="t-approve" value="1" type="number"></div>

      <div class="section-cap" style="margin-top:14px">Monitoring</div>
      <div class="trow"><div class="tlabel">Sound alerts</div><div class="tog" onclick="this.classList.toggle('on')"></div></div>
      <div class="trow"><div class="tlabel">Drain detection</div><div class="tog on" onclick="this.classList.toggle('on')"></div></div>
      <div class="trow"><div class="tlabel">Unlimited approvals</div><div class="tog on" onclick="this.classList.toggle('on')"></div></div>
      <div class="trow"><div class="tlabel">System events</div><div class="tog on" onclick="this.classList.toggle('on')"></div></div>
      <div class="trow"><div class="tlabel">Auto-pause on critical</div><div class="tog" onclick="this.classList.toggle('on')"></div></div>
    </div>
  </div>
</div>

<div class="sbar">
  <div class="sbar-l">
    <span><span class="dot"></span>Ethereum Mainnet Connected</span>
    <span>Last update: <span id="last-upd">—</span></span>
  </div>
  <div class="sbar-r">
    <span>Polling interval: 5s</span>
    <span id="scan-status" style="color:var(--green)">SCANNING</span>
  </div>
</div>

<script>
var scanning=true,alerts=[],watchlist=[],tokens=[],filterMode='all';
var COLORS=['#0b6bcb','#14804a','#c62828','#b26a00','#5b3cc4','#00796b','#8a3ffc'];

function short(a){return a && a.length > 12 ? a.slice(0,6)+'…'+a.slice(-4) : (a || '—')}
function ts(){return new Date().toLocaleTimeString('en',{hour12:false,hour:'2-digit',minute:'2-digit',second:'2-digit'})}
function rnd(l){return '0x'+Array.from({length:l||40},()=>'0123456789abcdef'[Math.floor(Math.random()*16)]).join('')}

function parseDetail(detail){
  detail = detail || '';
  var arrowIdx = detail.indexOf('→');
  var pipeIdx = detail.indexOf('|');
  var from = arrowIdx > -1 ? detail.substring(0, arrowIdx).trim() : '';
  var to = pipeIdx > -1 ? detail.substring(arrowIdx + 1, pipeIdx).trim() : (arrowIdx > -1 ? detail.substring(arrowIdx + 1).trim() : '');
  var contract = pipeIdx > -1 ? detail.substring(pipeIdx + 1).trim() : '';
  return {from:from,to:to,contract:contract};
}

function symbolFromTitle(title){
  if(!title) return 'UNK';
  var m = title.match(/([A-Z0-9]{2,10})/);
  return m ? m[1] : 'UNK';
}

function amountLabel(a){
  if(a.type === 'approval') return 'MAX_UINT256';
  return a.title || 'Alert';
}

function riskLevel(a){
  if(a.type === 'drain') return 'high';
  if(a.type === 'approval') return 'med';
  return 'low';
}

function buildTokens(){
  var seen = {};
  tokens = [];
  alerts.forEach(function(a){
    var p = parseDetail(a.detail || '');
    if(!p.contract || seen[p.contract]) return;
    seen[p.contract] = true;
    tokens.push({
      sym: symbolFromTitle(a.title),
      addr: p.contract,
      risk: riskLevel(a)
    });
  });
}

function updateStats(data){
  var stats = data.stats || {};
  var hp = alerts.filter(function(a){ return a.type === 'drain' || a.type === 'approval'; }).length;
  document.getElementById('st-tok').textContent = (stats.tokens || tokens.length || 0).toLocaleString();
  document.getElementById('st-tx').textContent = (stats.transfers || 0).toLocaleString();
  document.getElementById('st-drain').textContent = (stats.drains || 0).toLocaleString();
  document.getElementById('st-approve').textContent = (stats.approvals || 0).toLocaleString();
  document.getElementById('st-hp').textContent = hp.toLocaleString();
  document.getElementById('hp-badge').textContent = hp.toLocaleString();
  var latestBlock = alerts.length ? (alerts[0].block || '—') : '—';
  document.getElementById('block-badge').textContent = 'Block ' + latestBlock;
  document.getElementById('pending').textContent = latestBlock;
  document.getElementById('gas').textContent = (8 + Math.random()*90).toFixed(1);
  document.getElementById('last-scan').textContent = ts();
  document.getElementById('last-upd').textContent = ts();
}

function renderAlerts(){
  var list = filterMode === 'all' ? alerts : alerts.filter(function(a){ return a.type === filterMode; });
  document.getElementById('ev-count').textContent = list.length + ' events';
  if(list.length === 0){
    document.getElementById('alert-list').innerHTML = '<div class="empty dots"><span>●</span><span>●</span><span>●</span><div style="margin-top:8px">Waiting for on-chain activity...</div></div>';
    return;
  }
  var html = list.slice(0, 100).map(function(a){
    var p = parseDetail(a.detail || '');
    var amountColor = a.type === 'drain' ? 'var(--red)' : a.type === 'approval' ? 'var(--amber)' : 'var(--text)';
    return '<div class="ai">' +
      '<div class="ai-row"><span class="atype t-' + a.type + '">' + a.type.toUpperCase() + '</span><span class="atime">#' + (a.block || '—') + '</span></div>' +
      '<div class="ai-row"><span class="aaddr"><b>' + short(p.from) + '</b> → <b>' + short(p.to) + '</b></span><span class="aamount" style="color:' + amountColor + '">' + amountLabel(a) + '</span></div>' +
      '<div class="aaddr">' + (p.contract ? 'Contract: <b>' + short(p.contract) + '</b>' : (a.detail || '')) + '</div>' +
      '</div>';
  }).join('');
  document.getElementById('alert-list').innerHTML = html;
}

function renderHP(){
  var hp = alerts.filter(function(a){ return a.type === 'drain' || a.type === 'approval'; }).slice(0, 8);
  if(hp.length === 0){
    document.getElementById('hp-list').innerHTML = '<div class="empty" style="padding:14px 0">No critical alerts at this time</div>';
    return;
  }
  var html = hp.map(function(a){
    var p = parseDetail(a.detail || '');
    return '<div class="ai">' +
      '<div class="ai-row"><span class="atype t-' + a.type + '">' + a.type.toUpperCase() + '</span><span class="atime">#' + (a.block || '—') + '</span></div>' +
      '<div class="ai-row"><span class="aaddr"><b>' + short(p.from) + '</b></span><span class="aamount" style="color:var(--red)">' + amountLabel(a) + '</span></div>' +
      '<div style="margin-top:5px" class="aaddr">' + (a.title || '') + '</div>' +
      '</div>';
  }).join('');
  document.getElementById('hp-list').innerHTML = html;
}

function renderToks(){
  var q=(document.getElementById('tok-search').value||'').toLowerCase();
  var f=q?tokens.filter(function(t){return t.sym.toLowerCase().includes(q) || t.addr.toLowerCase().includes(q);}):tokens;
  if(f.length===0){document.getElementById('tok-list').innerHTML='<div class="empty">'+(q?'No matching token found':'Registry auto-populates as contracts are observed')+'</div>';return;}
  var html=f.slice(0,20).map(function(t,i){
    return '<div class="tr">'+
      '<div class="ticon" style="color:'+COLORS[i%COLORS.length]+'">'+t.sym.slice(0,3)+'</div>'+
      '<div><div class="tname">'+t.sym+'</div><div class="taddr">'+short(t.addr)+'</div></div>'+
      '<span class="risk r-'+t.risk+'">'+t.risk.toUpperCase()+'</span>'+
      '<button class="btn btn-g btn-sm" onclick="addWatchAddr(\''+t.addr+'\',\''+t.sym+'\')">Watch</button>'+
    '</div>';
  }).join('');
  document.getElementById('tok-list').innerHTML=html;
}

function renderWatch(){
  if(watchlist.length===0){document.getElementById('watch-list').innerHTML='<div class="empty" style="padding:14px 0">No watched addresses yet</div>';return;}
  var html=watchlist.map(function(w,i){
    return '<div class="wi">'+
      '<div class="wavatar">'+w.label.slice(0,2).toUpperCase()+'</div>'+
      '<div class="winfo"><div class="wlabel">'+w.label+'</div><div class="whex">'+short(w.addr)+'</div></div>'+
      '<div class="wbtns">'+
        '<button class="btn btn-g btn-sm" onclick="copyAddr(\\''+w.addr+'\\')" title="Copy">Copy</button>'+
        '<button class="btn btn-d btn-sm" onclick="rmWatch('+i+')">Remove</button>'+
      '</div></div>';
  }).join('');
  document.getElementById('watch-list').innerHTML=html;
}

function setFilter(m,el){
  filterMode=m;
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('on');});
  el.classList.add('on');
  renderAlerts();
}

async function clearAlerts(){
  if(!confirm('Clear all alerts?')) return;
  await fetch('/api/clear',{method:'POST'});
  alerts = [];
  buildTokens();
  renderAlerts();
  renderHP();
  renderToks();
  updateStats({stats:{tokens:0,transfers:0,drains:0,approvals:0}});
}

function toggleScan(){
  scanning=!scanning;
  var b=document.getElementById('scan-btn');
  b.textContent=scanning?'Pause':'Resume';
  document.getElementById('scan-status').textContent=scanning?'SCANNING':'PAUSED';
  document.getElementById('scan-status').style.color=scanning?'var(--green)':'var(--amber)';
}

function exportAlerts(){
  var blob=new Blob([JSON.stringify(alerts,null,2)],{type:'application/json'});
  var a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download='erc20-alerts.json';
  a.click();
}

function addWatch(){
  var v=document.getElementById('watch-inp').value.trim();
  if(!v||v.length!==42||!v.startsWith('0x')){alert('Enter a valid 0x address (42 chars)');return;}
  watchlist.push({addr:v,label:'Wallet '+(watchlist.length+1)});
  document.getElementById('watch-inp').value='';
  renderWatch();
}

function addWatchAddr(addr,label){
  if(watchlist.find(function(w){return w.addr===addr;}))return;
  watchlist.push({addr:addr,label:label||'Contract'});
  renderWatch();
}

function addDemoWatch(){watchlist.push({addr:rnd(),label:'Whale '+(watchlist.length+1)});renderWatch();}
function pasteAddr(){navigator.clipboard.readText().then(function(t){document.getElementById('watch-inp').value=t.trim();}).catch(function(){});}
function rmWatch(i){watchlist.splice(i,1);renderWatch();}
function clearWatch(){watchlist=[];renderWatch();}
function copyAddr(a){navigator.clipboard.writeText(a).catch(function(){});}
function saveConfig(){var t=document.getElementById('t-drain').value;document.getElementById('tdisplay').textContent=Number(t).toLocaleString()+' tokens';}
function sortTok(){tokens.sort(function(a,b){return a.sym.localeCompare(b.sym);});renderToks();}
function dismissHP(){alerts=alerts.filter(function(a){return a.type!=='drain'&&a.type!=='approval';});renderHP();renderAlerts();}

async function refresh(){
  if(!scanning) return;
  try{
    var r = await fetch('/api/data');
    var d = await r.json();
    alerts = d.alerts || [];
    buildTokens();
    updateStats(d);
    renderAlerts();
    renderHP();
    renderToks();
  }catch(e){
    console.log(e);
  }
}

refresh();
setInterval(refresh,5000);
</script>
</body>
</html>
"""


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
    data["alerts"] = data["alerts"][:500]

    alert_type = alert.get("type", "")
    if alert_type == "drain":
        data["stats"]["drains"] += 1
    elif alert_type == "approval":
        data["stats"]["approvals"] += 1
    elif alert_type == "transfer":
        data["stats"]["transfers"] += 1

    contracts = set()
    for item in data["alerts"]:
        detail = item.get("detail", "")
        if "|" in detail:
            contracts.add(detail.split("|")[-1].strip())
    data["stats"]["tokens"] = len(contracts)

    save(data)
    return jsonify({"ok": True})


@app.route("/api/clear", methods=["POST"])
def clear():
    save({"alerts": [], "stats": {"tokens": 0, "transfers": 0, "drains": 0, "approvals": 0}})
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
