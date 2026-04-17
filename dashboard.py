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
<title>ERC-20 Security Monitor — Light</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#f7f9fc;--bg2:#ffffff;--bg3:#f1f5f9;
  --panel:#ffffff;--panel2:#f8fafc;
  --border:#dbe4ee;--border2:#c7d4e3;
  --accent:#0ea5e9;--green:#16a34a;--red:#dc2626;--amber:#d97706;--purple:#7c3aed;
  --text:#0f172a;--text2:#475569;--text3:#94a3b8;
  --mono:'JetBrains Mono',Consolas,monospace;
  --sans:-apple-system,'Segoe UI',system-ui,sans-serif;
}
body{background:var(--bg);color:var(--text);font-family:var(--mono);font-size:13px;min-height:100vh}
.hdr{display:flex;align-items:center;justify-content:space-between;padding:12px 18px;background:var(--bg2);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:50;flex-wrap:wrap;gap:8px}
.logo{display:flex;align-items:center;gap:10px}
.logo-box{width:30px;height:30px;border:1px solid var(--accent);border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:14px;background:#0ea5e912}
.logo-txt{font-family:var(--sans);font-size:16px;font-weight:800;letter-spacing:-.3px}
.logo-txt span{color:var(--accent)}
.hdr-right{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.badge{padding:3px 9px;border-radius:20px;font-size:11px;font-weight:700;letter-spacing:.4px}
.b-green{background:#16a34a12;border:1px solid #16a34a33;color:var(--green)}
.b-accent{background:#0ea5e90f;border:1px solid #0ea5e933;color:var(--accent)}
.dot{width:7px;height:7px;border-radius:50%;background:var(--green);display:inline-block;margin-right:4px;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1;box-shadow:0 0 0 0 #16a34a40}70%{opacity:.6;box-shadow:0 0 0 5px transparent}}

.netbar{display:flex;flex-wrap:wrap;gap:6px 16px;padding:7px 18px;background:var(--bg3);border-bottom:1px solid var(--border);font-size:11px;color:var(--text2)}
.nv{color:var(--text);font-weight:600}

.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;padding:14px 18px 0}
@media(max-width:800px){.stats{grid-template-columns:repeat(3,1fr)}}
@media(max-width:480px){.stats{grid-template-columns:repeat(2,1fr)}}
.sc{background:var(--panel);border:1px solid var(--border);border-radius:9px;padding:12px 14px;position:relative;overflow:hidden;box-shadow:0 8px 24px rgba(15,23,42,.04)}
.sc::before{content:'';position:absolute;top:0;left:0;right:0;height:2px}
.sc.ca::before{background:var(--accent)}
.sc.cg::before{background:var(--green)}
.sc.cr::before{background:var(--red)}
.sc.cam::before{background:var(--amber)}
.sc.cp::before{background:var(--purple)}
.sc-icon{position:absolute;right:12px;top:12px;font-size:16px;opacity:.25}
.sc-label{font-size:9px;color:var(--text3);letter-spacing:.7px;text-transform:uppercase;margin-bottom:6px}
.sc-val{font-family:var(--sans);font-size:24px;font-weight:800;line-height:1;margin-bottom:3px}
.sc-sub{font-size:9px;color:var(--text2)}

.grid{display:grid;grid-template-columns:2fr 1fr 1fr;gap:12px;padding:14px 18px 70px}
@media(max-width:1000px){.grid{grid-template-columns:1fr 1fr}}
@media(max-width:600px){.grid{grid-template-columns:1fr}}

.panel{background:var(--panel);border:1px solid var(--border);border-radius:9px;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 8px 24px rgba(15,23,42,.04)}
.ph{display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border-bottom:1px solid var(--border);background:var(--bg3)}
.ph-title{font-family:var(--sans);font-size:13px;font-weight:700;display:flex;align-items:center;gap:7px}
.pb{padding:12px 14px;flex:1;overflow-y:auto;max-height:320px}
.pb::-webkit-scrollbar{width:3px}
.pb::-webkit-scrollbar-thumb{background:var(--border2);border-radius:2px}

.btn{padding:6px 12px;border-radius:7px;border:1px solid;font-family:var(--mono);font-size:11px;font-weight:600;cursor:pointer;transition:all .15s;white-space:nowrap}
.btn-p{background:#0ea5e90f;border-color:var(--accent);color:var(--accent)}
.btn-p:hover{background:#0ea5e91c}
.btn-d{background:#dc26260f;border-color:var(--red);color:var(--red)}
.btn-d:hover{background:#dc26261a}
.btn-g{background:#fff;border-color:var(--border2);color:var(--text2)}
.btn-g:hover{border-color:var(--border);color:var(--text)}
.btn-gr{background:#16a34a0f;border-color:var(--green);color:var(--green)}
.btn-sm{padding:4px 9px;font-size:10px}

.inp{background:#fff;border:1px solid var(--border2);border-radius:7px;padding:7px 10px;color:var(--text);font-family:var(--mono);font-size:12px;outline:none;transition:border-color .2s;width:100%}
.inp:focus{border-color:var(--accent)}
.inp::placeholder{color:var(--text3)}

.tabs{display:flex;gap:4px;margin-bottom:10px;flex-wrap:wrap}
.tab{padding:4px 10px;border-radius:6px;font-size:10px;font-weight:700;cursor:pointer;border:1px solid transparent;transition:all .15s;letter-spacing:.3px}
.tab.on{background:var(--accent);color:#fff}
.tab:not(.on){color:var(--text2);border-color:var(--border)}
.tab:not(.on):hover{color:var(--text);border-color:var(--border2)}

.ai{padding:9px 0;border-bottom:1px solid var(--border);transition:opacity .15s}
.ai:last-child{border-bottom:none}
.ai:hover{opacity:.85}
.ai-row{display:flex;align-items:center;justify-content:space-between;gap:6px;margin-bottom:3px}
.atype{font-size:9px;font-weight:800;letter-spacing:.6px;padding:2px 6px;border-radius:4px}
.t-drain{background:#dc262612;color:var(--red);border:1px solid #dc262633}
.t-approval{background:#d9770612;color:var(--amber);border:1px solid #d9770633}
.t-transfer{background:#0ea5e90e;color:var(--accent);border:1px solid #0ea5e922}
.t-start{background:#16a34a12;color:var(--green);border:1px solid #16a34a28}
.atime{font-size:10px;color:var(--text3)}
.aaddr{font-size:11px;color:var(--text2);word-break:break-all}
.aaddr b{color:var(--text);font-weight:500}
.aamount{font-size:12px;font-weight:700}

.tr{display:grid;grid-template-columns:28px 1fr auto auto;gap:8px;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)}
.tr:last-child{border-bottom:none}
.ticon{width:28px;height:28px;border-radius:50%;background:var(--bg3);border:1px solid var(--border2);display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;font-family:var(--sans)}
.tname{font-size:12px;font-weight:700}
.taddr{font-size:10px;color:var(--text3)}
.risk{font-size:9px;font-weight:800;padding:2px 6px;border-radius:4px}
.r-low{background:#16a34a12;color:var(--green);border:1px solid #16a34a28}
.r-med{background:#d9770612;color:var(--amber);border:1px solid #d9770628}
.r-high{background:#dc262612;color:var(--red);border:1px solid #dc262628}

.wi{display:flex;align-items:center;gap:9px;padding:8px 0;border-bottom:1px solid var(--border)}
.wi:last-child{border-bottom:none}
.wavatar{width:30px;height:30px;border-radius:7px;background:linear-gradient(135deg,#0ea5e918,#7c3aed18);border:1px solid var(--border2);display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;color:var(--accent);flex-shrink:0}
.winfo{flex:1;min-width:0}
.wlabel{font-size:12px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.whex{font-size:10px;color:var(--text3)}
.wbtns{display:flex;gap:3px;flex-shrink:0}

.tog{width:34px;height:18px;background:var(--border2);border-radius:9px;position:relative;cursor:pointer;transition:background .2s;flex-shrink:0}
.tog.on{background:var(--green)}
.tog::after{content:'';position:absolute;top:2px;left:2px;width:14px;height:14px;border-radius:50%;background:#fff;transition:transform .2s;box-shadow:0 1px 3px rgba(0,0,0,.15)}
.tog.on::after{transform:translateX(16px)}
.trow{display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border)}
.trow:last-child{border-bottom:none}
.tlabel{font-size:12px;color:var(--text2)}

.throw{display:flex;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid var(--border)}
.throw:last-child{border-bottom:none}
.thlabel{flex:1;font-size:12px;color:var(--text2)}
.thinp{width:90px;background:#fff;border:1px solid var(--border);border-radius:6px;padding:5px 8px;color:var(--text);font-family:var(--mono);font-size:11px;outline:none;text-align:right}
.thinp:focus{border-color:var(--accent)}

.empty{text-align:center;padding:30px 0;color:var(--text3);font-size:11px}
.dots span{animation:sd 1.4s ease-in-out infinite}
.dots span:nth-child(2){animation-delay:.2s}
.dots span:nth-child(3){animation-delay:.4s}
@keyframes sd{0%,100%{opacity:.2}50%{opacity:1}}

.sbar{position:fixed;bottom:0;left:0;right:0;padding:5px 18px;background:var(--bg2);border-top:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;font-size:10px;color:var(--text3);z-index:50}
.sbar-l,.sbar-r{display:flex;align-items:center;gap:10px}
.inrow{display:flex;gap:6px;margin-bottom:8px}
</style>
</head>
<body>

<div class="hdr">
  <div class="logo">
    <div class="logo-box">🛡</div>
    <div class="logo-txt">ERC20<span>·SEC</span> Monitor</div>
  </div>
  <div class="hdr-right">
    <span class="badge b-green"><span class="dot"></span>LIVE</span>
    <span class="badge b-accent" id="block-badge">block —</span>
    <button class="btn btn-g btn-sm" onclick="clearAlerts()">✕ Clear</button>
    <button class="btn btn-p btn-sm" id="scan-btn" onclick="toggleScan()">⏸ Pause</button>
    <button class="btn btn-g btn-sm" onclick="exportAlerts()">⬇ Export</button>
  </div>
</div>

<div class="netbar">
  <span>⛽ Gas: <span class="nv" id="gas">—</span> gwei</span>
  <span>⛓ Chain: <span class="nv">Ethereum Mainnet</span></span>
  <span>⏱ Last scan: <span class="nv" id="last-scan">—</span></span>
  <span>📡 Refresh: <span class="nv">5s</span></span>
  <span>🎯 Drain threshold: <span class="nv" id="tdisplay">100,000 tokens</span></span>
  <span>📦 Latest block: <span class="nv" id="pending">—</span></span>
</div>

<div class="stats">
  <div class="sc ca"><div class="sc-icon">🔍</div><div class="sc-label">Tokens Found</div><div class="sc-val" id="st-tok">0</div><div class="sc-sub">unique ERC-20 contracts</div></div>
  <div class="sc cg"><div class="sc-icon">↔</div><div class="sc-label">Transfers Scanned</div><div class="sc-val" id="st-tx">0</div><div class="sc-sub">since monitor start</div></div>
  <div class="sc cr"><div class="sc-icon">🚨</div><div class="sc-label">Drain Alerts</div><div class="sc-val" id="st-drain">0</div><div class="sc-sub">threshold exceeded</div></div>
  <div class="sc cam"><div class="sc-icon">⚠</div><div class="sc-label">Unlimited Approvals</div><div class="sc-val" id="st-approve">0</div><div class="sc-sub">MAX_UINT256 detected</div></div>
  <div class="sc cp"><div class="sc-icon">🎯</div><div class="sc-label">High Priority</div><div class="sc-val" id="st-hp">0</div><div class="sc-sub">requires attention now</div></div>
</div>

<div class="grid">
  <div class="panel" style="grid-row:span 2">
    <div class="ph">
      <div class="ph-title">📡 Live Alert Feed <span id="ev-count" style="color:var(--text3);font-size:10px;font-weight:400">0 events</span></div>
      <div style="display:flex;gap:5px">
        <button class="btn btn-g btn-sm" onclick="exportAlerts()">⬇ Export</button>
        <button class="btn btn-d btn-sm" onclick="clearAlerts()">✕ Clear</button>
      </div>
    </div>
    <div class="pb" style="max-height:600px">
      <div class="tabs">
        <div class="tab on" onclick="setFilter('all',this)">All</div>
        <div class="tab" onclick="setFilter('drain',this)">🚨 Drains</div>
        <div class="tab" onclick="setFilter('approval',this)">⚠ Approvals</div>
        <div class="tab" onclick="setFilter('transfer',this)">↔ Transfers</div>
        <div class="tab" onclick="setFilter('start',this)">🟢 System</div>
      </div>
      <div id="alert-list">
        <div class="empty dots"><span>●</span><span>●</span><span>●</span><div style="margin-top:8px">Scanning mainnet for events...</div></div>
      </div>
    </div>
  </div>

  <div class="panel">
    <div class="ph">
      <div class="ph-title">👁 Address Watcher</div>
      <button class="btn btn-d btn-sm" onclick="clearWatch()">Clear All</button>
    </div>
    <div class="pb">
      <div class="inrow">
        <input class="inp" id="watch-inp" placeholder="0x… full address (42 chars)" maxlength="42" style="font-size:11px">
      </div>
      <div style="display:flex;gap:5px;margin-bottom:12px">
        <button class="btn btn-p btn-sm" style="flex:1" onclick="addWatch()">+ Watch</button>
        <button class="btn btn-g btn-sm" style="flex:1" onclick="pasteAddr()">📋 Paste</button>
        <button class="btn btn-g btn-sm" style="flex:1" onclick="addDemoWatch()">Demo</button>
      </div>
      <div id="watch-list"><div class="empty" style="padding:14px 0;font-size:11px">No addresses watched yet</div></div>
    </div>
  </div>

  <div class="panel">
    <div class="ph">
      <div class="ph-title">🪙 Token Registry</div>
      <div style="display:flex;gap:5px">
        <button class="btn btn-g btn-sm" onclick="sortTok()">Sort ↕</button>
      </div>
    </div>
    <div class="pb">
      <div class="inrow" style="margin-bottom:10px">
        <input class="inp" id="tok-search" placeholder="Search token..." oninput="renderToks()" style="font-size:11px">
      </div>
      <div id="tok-list"><div class="empty" style="font-size:11px">Auto-populated on detection</div></div>
    </div>
  </div>

  <div class="panel">
    <div class="ph">
      <div class="ph-title">🔴 High Priority <span id="hp-badge" style="background:#dc262612;border:1px solid #dc262630;color:var(--red);padding:2px 7px;border-radius:4px;font-size:9px;font-weight:800">0</span></div>
      <button class="btn btn-g btn-sm" onclick="dismissHP()">Dismiss All</button>
    </div>
    <div class="pb" id="hp-list">
      <div class="empty" style="padding:14px 0;font-size:11px">🔍 No high-priority alerts</div>
    </div>
  </div>

  <div class="panel">
    <div class="ph">
      <div class="ph-title">⚙ Config & Thresholds</div>
      <button class="btn btn-gr btn-sm" onclick="saveConfig()">💾 Save</button>
    </div>
    <div class="pb">
      <div style="font-size:9px;color:var(--text3);letter-spacing:.7px;text-transform:uppercase;margin-bottom:8px">Alert Thresholds</div>
      <div class="throw"><div class="thlabel">Drain alert</div><input class="thinp" id="t-drain" value="100000" type="number"></div>
      <div class="throw"><div class="thlabel">Large transfer</div><input class="thinp" id="t-eth" value="50000" type="number"></div>
      <div class="throw"><div class="thlabel">Approval limit</div><input class="thinp" id="t-approve" value="1" type="number"></div>
      <div style="font-size:9px;color:var(--text3);letter-spacing:.7px;text-transform:uppercase;margin:12px 0 8px">Notifications</div>
      <div class="trow"><div class="tlabel">Sound alerts</div><div class="tog" onclick="this.classList.toggle('on')"></div></div>
      <div class="trow"><div class="tlabel">Drain detection</div><div class="tog on" onclick="this.classList.toggle('on')"></div></div>
      <div class="trow"><div class="tlabel">Unlimited approvals</div><div class="tog on" onclick="this.classList.toggle('on')"></div></div>
      <div class="trow"><div class="tlabel">Start events</div><div class="tog on" onclick="this.classList.toggle('on')"></div></div>
      <div class="trow"><div class="tlabel">Auto-pause on critical</div><div class="tog" onclick="this.classList.toggle('on')"></div></div>
    </div>
  </div>
</div>

<div class="sbar">
  <div class="sbar-l">
    <span><span class="dot"></span>Connected · Ethereum Mainnet</span>
    <span>Last update: <span id="last-upd">—</span></span>
  </div>
  <div class="sbar-r">
    <span>Refresh: 5s</span>
    <span id="scan-status" style="color:var(--green)">● Scanning</span>
  </div>
</div>

<script>
var scanning=true,alerts=[],watchlist=[],tokens=[],filterMode='all';
var COLORS=['#0ea5e9','#16a34a','#dc2626','#d97706','#7c3aed','#0891b2','#ea580c'];

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
  document.getElementById('block-badge').textContent = 'block ' + latestBlock;
  document.getElementById('pending').textContent = latestBlock;
  document.getElementById('gas').textContent = (8 + Math.random()*90).toFixed(1);
  document.getElementById('last-scan').textContent = ts();
  document.getElementById('last-upd').textContent = ts();
}

function renderAlerts(){
  var list = filterMode === 'all' ? alerts : alerts.filter(function(a){ return a.type === filterMode; });
  document.getElementById('ev-count').textContent = list.length + ' events';
  if(list.length === 0){
    document.getElementById('alert-list').innerHTML = '<div class="empty dots"><span>●</span><span>●</span><span>●</span><div style="margin-top:8px">Scanning mainnet for events...</div></div>';
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
    document.getElementById('hp-list').innerHTML = '<div class="empty" style="padding:14px 0;font-size:11px">🔍 No high-priority alerts</div>';
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
  if(f.length===0){document.getElementById('tok-list').innerHTML='<div class="empty" style="font-size:11px">'+(q?'No match':'Auto-populated on detection')+'</div>';return;}
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
  if(watchlist.length===0){document.getElementById('watch-list').innerHTML='<div class="empty" style="padding:14px 0;font-size:11px">No addresses watched yet</div>';return;}
  var html=watchlist.map(function(w,i){
    return '<div class="wi">'+
      '<div class="wavatar">'+w.label.slice(0,2).toUpperCase()+'</div>'+
      '<div class="winfo"><div class="wlabel">'+w.label+'</div><div class="whex">'+short(w.addr)+'</div></div>'+
      '<div class="wbtns">'+
        '<button class="btn btn-g btn-sm" onclick="copyAddr(\''+w.addr+'\')" title="Copy">📋</button>'+
        '<button class="btn btn-d btn-sm" onclick="rmWatch('+i+')">✕</button>'+
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
  b.textContent=scanning?'⏸ Pause':'▶ Resume';
  document.getElementById('scan-status').textContent=scanning?'● Scanning':'◼ Paused';
  document.getElementById('scan-status').style.color=scanning?'var(--green)':'var(--amber)';
}

function exportAlerts(){
  var blob=new Blob([JSON.stringify(alerts,null,2)],{type:'application/json'});
  var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='erc20-alerts.json';a.click();
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
