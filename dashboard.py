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
  --bg:#080b10;--surface:#0d1117;--surface2:#161b22;--border:#21262d;--border2:#30363d;
  --text:#e6edf3;--muted:#7d8590;--dim:#484f58;
  --green:#3fb950;--green-bg:#0d1f0f;
  --red:#f85149;--red-bg:#1f0d0d;
  --yellow:#d29922;--yellow-bg:#1f1a0d;
  --blue:#58a6ff;--blue-bg:#0d1526;
  --purple:#bc8cff;--purple-bg:#1a0d2e;
}
*{box-sizing:border-box;margin:0;padding:0;}
html,body{height:100%;}
body{font-family:'Syne',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden;}
.mono{font-family:'JetBrains Mono',monospace;}
body::before{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(63,185,80,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(63,185,80,0.03) 1px,transparent 1px);background-size:40px 40px;pointer-events:none;z-index:0;}
.app{position:relative;z-index:1;display:flex;flex-direction:column;min-height:100vh;}
.topbar{display:flex;align-items:center;justify-content:space-between;padding:1rem 1.5rem;border-bottom:1px solid var(--border);background:rgba(8,11,16,0.9);backdrop-filter:blur(12px);position:sticky;top:0;z-index:100;}
.brand{display:flex;align-items:center;gap:12px;}
.brand-icon{width:36px;height:36px;background:var(--green-bg);border:1px solid var(--green);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px;}
.brand-name{font-size:1rem;font-weight:800;letter-spacing:-0.02em;}
.brand-sub{font-size:11px;color:var(--muted);font-family:'JetBrains Mono',monospace;margin-top:1px;}
.topbar-right{display:flex;align-items:center;gap:10px;}
.live-badge{display:flex;align-items:center;gap:6px;background:var(--green-bg);border:1px solid rgba(63,185,80,0.3);border-radius:20px;padding:4px 12px;font-size:11px;font-weight:600;color:var(--green);font-family:'JetBrains Mono',monospace;}
.live-dot{width:6px;height:6px;border-radius:50%;background:var(--green);animation:blink 1.4s infinite;}
@keyframes blink{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.3;transform:scale(0.8)}}
.block-badge{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:4px 10px;}
.clear-btn{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);background:transparent;border:1px solid var(--border);border-radius:6px;padding:4px 10px;cursor:pointer;transition:all .15s;}
.clear-btn:hover{border-color:var(--red);color:var(--red);}
.main{flex:1;padding:1.5rem;display:flex;flex-direction:column;gap:1.25rem;}
.stats-row{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;}
.stat-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:1.25rem;position:relative;overflow:hidden;transition:border-color .2s;}
.stat-card:hover{border-color:var(--border2);}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;}
.stat-card.tokens::before{background:var(--blue);}
.stat-card.transfers::before{background:var(--purple);}
.stat-card.drains::before{background:var(--red);}
.stat-card.approvals::before{background:var(--yellow);}
.stat-label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px;font-family:'JetBrains Mono',monospace;}
.stat-value{font-size:2.2rem;font-weight:800;line-height:1;margin-bottom:6px;}
.stat-card.tokens .stat-value{color:var(--blue);}
.stat-card.transfers .stat-value{color:var(--purple);}
.stat-card.drains .stat-value{color:var(--red);}
.stat-card.approvals .stat-value{color:var(--yellow);}
.stat-sub{font-size:11px;color:var(--dim);font-family:'JetBrains Mono',monospace;}
.content-grid{display:grid;grid-template-columns:1fr 380px;gap:1.25rem;flex:1;}
.panel{background:var(--surface);border:1px solid var(--border);border-radius:12px;display:flex;flex-direction:column;overflow:hidden;}
.panel-header{display:flex;align-items:center;justify-content:space-between;padding:1rem 1.25rem;border-bottom:1px solid var(--border);background:var(--surface2);flex-shrink:0;}
.panel-title{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted);font-family:'JetBrains Mono',monospace;}
.panel-count{font-size:11px;font-family:'JetBrains Mono',monospace;color:var(--dim);background:var(--surface);border:1px solid var(--border);border-radius:20px;padding:2px 10px;}
.toolbar{display:flex;align-items:center;gap:8px;padding:0.6rem 1.25rem;border-bottom:1px solid var(--border);background:var(--surface);flex-shrink:0;}
.filter-tabs{display:flex;gap:4px;flex:1;overflow-x:auto;}
.tab{font-size:11px;font-family:'JetBrains Mono',monospace;padding:4px 12px;border-radius:20px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;transition:all .15s;white-space:nowrap;}
.tab:hover{border-color:var(--border2);color:var(--text);}
.tab.active{background:var(--surface2);border-color:var(--border2);color:var(--text);}
.tab.active.drain{border-color:var(--red);color:var(--red);background:var(--red-bg);}
.tab.active.approval{border-color:var(--yellow);color:var(--yellow);background:var(--yellow-bg);}
.tab.active.transfer{border-color:var(--purple);color:var(--purple);background:var(--purple-bg);}
.search-box{background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:4px 10px;color:var(--text);font-size:11px;font-family:'JetBrains Mono',monospace;width:180px;outline:none;transition:border-color .15s;}
.search-box:focus{border-color:var(--border2);}
.search-box::placeholder{color:var(--dim);}
.feed-scroll{flex:1;overflow-y:auto;min-height:0;max-height:520px;}
.feed-scroll::-webkit-scrollbar{width:4px;}
.feed-scroll::-webkit-scrollbar-thumb{background:var(--border2);border-radius:4px;}
.alert-item{display:flex;gap:12px;padding:12px 1.25rem;border-bottom:1px solid var(--border);transition:background .15s;cursor:pointer;animation:slideIn .3s ease;}
@keyframes slideIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}
.alert-item:hover{background:var(--surface2);}
.alert-item.is-drain{border-left:2px solid var(--red);}
.alert-item.is-approval{border-left:2px solid var(--yellow);}
.alert-dot{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;flex-shrink:0;margin-top:1px;font-family:'JetBrains Mono',monospace;}
.dot-drain{background:var(--red-bg);color:var(--red);border:1px solid rgba(248,81,73,0.2);}
.dot-approval{background:var(--yellow-bg);color:var(--yellow);border:1px solid rgba(210,153,34,0.2);}
.dot-transfer{background:var(--purple-bg);color:var(--purple);border:1px solid rgba(188,140,255,0.2);}
.dot-start{background:var(--green-bg);color:var(--green);border:1px solid rgba(63,185,80,0.2);}
.alert-body{flex:1;min-width:0;}
.alert-title{font-size:13px;font-weight:600;color:var(--text);margin-bottom:4px;}
.alert-detail{font-size:11px;color:var(--muted);font-family:'JetBrains Mono',monospace;word-break:break-all;line-height:1.5;}
.alert-detail.collapsed{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;word-break:normal;}
.alert-meta{display:flex;flex-direction:column;align-items:flex-end;gap:4px;flex-shrink:0;}
.alert-block{font-size:10px;font-family:'JetBrains Mono',monospace;color:var(--dim);background:var(--surface2);border:1px solid var(--border);border-radius:4px;padding:2px 6px;white-space:nowrap;}
.copy-btn{font-size:10px;padding:2px 8px;border-radius:4px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-family:'JetBrains Mono',monospace;transition:all .15s;white-space:nowrap;}
.copy-btn:hover{border-color:var(--green);color:var(--green);}
.copy-btn.copied{border-color:var(--green);color:var(--green);background:var(--green-bg);}
.expand-btn{font-size:10px;padding:2px 6px;border-radius:4px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-family:'JetBrains Mono',monospace;}
.expand-btn:hover{color:var(--text);border-color:var(--border2);}
.empty-state{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:3rem 1rem;gap:12px;color:var(--dim);}
.empty-icon{font-size:2rem;opacity:0.4;}
.empty-text{font-size:13px;font-family:'JetBrains Mono',monospace;}
.side-panel{display:flex;flex-direction:column;gap:1.25rem;}
.activity-scroll{flex:1;overflow-y:auto;min-height:0;max-height:420px;}
.activity-scroll::-webkit-scrollbar{width:4px;}
.activity-scroll::-webkit-scrollbar-thumb{background:var(--border2);border-radius:4px;}
.activity-item{display:flex;align-items:flex-start;gap:10px;padding:12px 1.25rem;border-bottom:1px solid var(--border);cursor:pointer;transition:background .15s;}
.activity-item:hover{background:var(--surface2);}
.activity-line{display:flex;flex-direction:column;flex:1;min-width:0;}
.activity-title{font-size:12px;font-weight:600;color:var(--text);margin-bottom:2px;}
.activity-addr{font-size:10px;font-family:'JetBrains Mono',monospace;color:var(--muted);word-break:break-all;}
.activity-block{font-size:10px;font-family:'JetBrains Mono',monospace;color:var(--dim);margin-top:2px;}
.status-bar{display:flex;align-items:center;justify-content:space-between;padding:0.6rem 1.5rem;border-top:1px solid var(--border);background:var(--surface);font-size:11px;font-family:'JetBrains Mono',monospace;color:var(--dim);}
.status-left{display:flex;align-items:center;gap:16px;}
.toast-container{position:fixed;top:70px;right:20px;z-index:999;display:flex;flex-direction:column;gap:8px;}
.toast{background:var(--surface2);border:1px solid var(--border2);border-radius:10px;padding:12px 16px;font-size:12px;font-family:'JetBrains Mono',monospace;color:var(--text);min-width:280px;max-width:360px;animation:toastIn .3s ease;box-shadow:0 4px 20px rgba(0,0,0,0.4);}
.toast.drain{border-color:var(--red);background:var(--red-bg);}
.toast.approval{border-color:var(--yellow);background:var(--yellow-bg);}
.toast-title{font-weight:700;margin-bottom:4px;}
.toast.drain .toast-title{color:var(--red);}
.toast.approval .toast-title{color:var(--yellow);}
.toast-detail{color:var(--muted);font-size:11px;word-break:break-all;}
@keyframes toastIn{from{opacity:0;transform:translateX(20px)}to{opacity:1;transform:translateX(0)}}
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.75);z-index:1000;display:flex;align-items:center;justify-content:center;padding:1rem;}
.modal{background:var(--surface);border:1px solid var(--border2);border-radius:14px;padding:1.5rem;width:100%;max-width:560px;max-height:85vh;overflow-y:auto;}
.modal-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:1.25rem;}
.modal-title{font-size:14px;font-weight:700;color:var(--text);font-family:'JetBrains Mono',monospace;}
.modal-close{background:transparent;border:1px solid var(--border);color:var(--muted);border-radius:6px;padding:4px 12px;cursor:pointer;font-size:12px;font-family:'JetBrains Mono',monospace;transition:all .15s;}
.modal-close:hover{color:var(--text);border-color:var(--border2);}
.modal-badge{display:inline-block;font-size:11px;padding:3px 10px;border-radius:20px;font-weight:600;font-family:'JetBrains Mono',monospace;margin-bottom:1rem;}
.modal-badge.drain{background:var(--red-bg);color:var(--red);border:1px solid rgba(248,81,73,0.3);}
.modal-badge.approval{background:var(--yellow-bg);color:var(--yellow);border:1px solid rgba(210,153,34,0.3);}
.modal-badge.transfer{background:var(--purple-bg);color:var(--purple);border:1px solid rgba(188,140,255,0.3);}
.modal-row{margin-bottom:1rem;}
.modal-label{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;font-family:'JetBrains Mono',monospace;}
.modal-val{font-size:12px;color:var(--text);word-break:break-all;background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:8px 12px;display:flex;justify-content:space-between;align-items:center;gap:8px;font-family:'JetBrains Mono',monospace;}
.modal-val span{flex:1;word-break:break-all;}
.etherscan-btn{font-size:11px;padding:4px 10px;border-radius:6px;border:1px solid rgba(88,166,255,0.3);background:var(--blue-bg);color:var(--blue);cursor:pointer;text-decoration:none;display:inline-block;font-family:'JetBrains Mono',monospace;transition:all .15s;}
.etherscan-btn:hover{border-color:var(--blue);background:rgba(88,166,255,0.15);}
@media(max-width:900px){.stats-row{grid-template-columns:repeat(2,1fr)}.content-grid{grid-template-columns:1fr}.side-panel{display:none}}
</style>
</head>
<body>
<div class="app">
  <div class="topbar">
    <div class="brand">
      <div class="brand-icon">🛡</div>
      <div>
        <div class="brand-name">ERC-20 Security Monitor</div>
        <div class="brand-sub mono">ethereum mainnet · auto-scan</div>
      </div>
    </div>
    <div class="topbar-right">
      <button class="clear-btn mono" onclick="clearAll()">Clear Alerts</button>
      <div class="block-badge mono" id="blockBadge">block —</div>
      <div class="live-badge"><span class="live-dot"></span>LIVE</div>
    </div>
  </div>
  <div class="main">
    <div class="stats-row">
      <div class="stat-card tokens"><div class="stat-label">Tokens Discovered</div><div class="stat-value mono" id="sTokens">0</div><div class="stat-sub">unique ERC20 contracts</div></div>
      <div class="stat-card transfers"><div class="stat-label">Transfers Scanned</div><div class="stat-value mono" id="sTransfers">0</div><div class="stat-sub">since monitor start</div></div>
      <div class="stat-card drains"><div class="stat-label">Drain Alerts</div><div class="stat-value mono" id="sDrains">0</div><div class="stat-sub">threshold exceeded</div></div>
      <div class="stat-card approvals"><div class="stat-label">Unlimited Approvals</div><div class="stat-value mono" id="sApprovals">0</div><div class="stat-sub">MAX_UINT256 detected</div></div>
    </div>
    <div class="content-grid">
      <div class="panel">
        <div class="panel-header">
          <span class="panel-title">Live Alert Feed</span>
          <span class="panel-count mono" id="feedCount">0 events</span>
        </div>
        <div class="toolbar">
          <div class="filter-tabs">
            <button class="tab active all" onclick="setFilter('all',this)">All</button>
            <button class="tab" onclick="setFilter('drain',this)">Drains</button>
            <button class="tab" onclick="setFilter('approval',this)">Approvals</button>
            <button class="tab" onclick="setFilter('transfer',this)">Transfers</button>
          </div>
          <input class="search-box mono" id="searchBox" placeholder="Search token, address..." oninput="renderFeed()">
        </div>
        <div class="feed-scroll" id="alertFeed">
          <div class="empty-state"><div class="empty-icon">📡</div><div class="empty-text">Scanning mainnet for events...</div></div>
        </div>
      </div>
      <div class="side-panel">
        <div class="panel" style="flex:1;">
          <div class="panel-header">
            <span class="panel-title">High Priority</span>
            <span class="panel-count mono" id="highCount">0</span>
          </div>
          <div class="activity-scroll" id="highFeed">
            <div class="empty-state" style="padding:2rem 1rem;"><div class="empty-icon" style="font-size:1.5rem;">🔍</div><div class="empty-text">No high-priority alerts</div></div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div class="status-bar">
    <div class="status-left">
      <span style="color:var(--green)">●</span> Connected to Ethereum Mainnet
      <span id="lastUpdate">Last update: —</span>
    </div>
    <span>Refreshing every 5s</span>
  </div>
</div>
<div class="toast-container" id="toastContainer"></div>
<script>
const ICONS={drain:'D',approval:'!',transfer:'T',start:'✓'};
const DOT={drain:'dot-drain',approval:'dot-approval',transfer:'dot-transfer',start:'dot-start'};
let allAlerts=[];
let currentFilter='all';
let lastCount=0;
let expandedItems=new Set();

function setFilter(f,el){
  currentFilter=f;
  document.querySelectorAll('.tab').forEach(t=>t.className='tab');
  el.className=`tab active ${f}`;
  renderFeed();
}

function copyText(text,btn){
  navigator.clipboard.writeText(text).then(()=>{
    const orig=btn.textContent;
    btn.textContent='Copied!';
    btn.classList.add('copied');
    setTimeout(()=>{btn.textContent=orig;btn.classList.remove('copied');},1500);
  });
}

function parseDetail(detail){
  const arrowIdx=detail.indexOf('→');
  const pipeIdx=detail.indexOf('|');
  const from=arrowIdx>-1?detail.substring(0,arrowIdx).trim():'';
  const to=pipeIdx>-1?detail.substring(arrowIdx+1,pipeIdx).trim():arrowIdx>-1?detail.substring(arrowIdx+1).trim():'';
  const contract=pipeIdx>-1?detail.substring(pipeIdx+1).trim():'';
  return{from,to,contract};
}

function showModal(idx){
  const a=allAlerts[idx];
  if(!a)return;
  const{from,to,contract}=parseDetail(a.detail);
  const existing=document.getElementById('alertModal');
  if(existing)existing.remove();
  const overlay=document.createElement('div');
  overlay.className='modal-overlay';
  overlay.id='alertModal';
  overlay.innerHTML=`
    <div class="modal">
      <div class="modal-header">
        <span class="modal-title">${a.title}</span>
        <button class="modal-close" onclick="document.getElementById('alertModal').remove()">✕ Close</button>
      </div>
      <span class="modal-badge ${a.type}">${a.type.toUpperCase()}</span>
      &nbsp;<span style="color:var(--muted);font-size:11px;font-family:'JetBrains Mono',monospace;">Block ${a.block}</span>
      ${from?`
      <div class="modal-row" style="margin-top:1rem;">
        <div class="modal-label">From Address</div>
        <div class="modal-val"><span>${from}</span><button class="copy-btn" onclick="copyText('${from}',this)">Copy</button></div>
      </div>`:''}
      ${to?`
      <div class="modal-row">
        <div class="modal-label">To Address</div>
        <div class="modal-val"><span>${to}</span><button class="copy-btn" onclick="copyText('${to}',this)">Copy</button></div>
      </div>`:''}
      ${contract?`
      <div class="modal-row">
        <div class="modal-label">Contract Address</div>
        <div class="modal-val"><span>${contract}</span><button class="copy-btn" onclick="copyText('${contract}',this)">Copy</button></div>
      </div>`:''}
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:0.5rem;">
        ${from?`<a class="etherscan-btn" href="https://etherscan.io/address/${from}" target="_blank">↗ From on Etherscan</a>`:''}
        ${to?`<a class="etherscan-btn" href="https://etherscan.io/address/${to}" target="_blank">↗ To on Etherscan</a>`:''}
        ${contract?`<a class="etherscan-btn" href="https://etherscan.io/token/${contract}" target="_blank">↗ Token on Etherscan</a>`:''}
      </div>
    </div>`;
  overlay.addEventListener('click',e=>{if(e.target===overlay)overlay.remove();});
  document.body.appendChild(overlay);
}

function toggleExpand(i,btn){
  if(expandedItems.has(i)){expandedItems.delete(i);btn.textContent='▼';}
  else{expandedItems.add(i);btn.textContent='▲';}
  renderFeed();
}

function renderFeed(){
  const feed=document.getElementById('alertFeed');
  const q=document.getElementById('searchBox').value.toLowerCase();
  let filtered=currentFilter==='all'?allAlerts:allAlerts.filter(a=>a.type===currentFilter);
  if(q)filtered=filtered.filter(a=>(a.title+a.detail).toLowerCase().includes(q));
  document.getElementById('feedCount').textContent=`${filtered.length} events`;
  if(!filtered.length){
    feed.innerHTML=`<div class="empty-state"><div class="empty-icon">📡</div><div class="empty-text">No events found...</div></div>`;
    return;
  }
  feed.innerHTML=filtered.map((a,i)=>{
    const realIdx=allAlerts.indexOf(a);
    const isExpanded=expandedItems.has(realIdx);
    const safeDetail=a.detail.replace(/\\/g,'\\\\').replace(/'/g,"\\'");
    return `<div class="alert-item${a.type==='drain'?' is-drain':a.type==='approval'?' is-approval':''}" onclick="showModal(${realIdx})">
      <div class="alert-dot ${DOT[a.type]||'dot-start'}">${ICONS[a.type]||'?'}</div>
      <div class="alert-body">
        <div class="alert-title">${a.title}</div>
        <div class="alert-detail${isExpanded?'':' collapsed'}">${a.detail}</div>
      </div>
      <div class="alert-meta">
        <div class="alert-block">⬡ ${a.block}</div>
        <button class="copy-btn" onclick="event.stopPropagation();copyText('${safeDetail}',this)">Copy</button>
        <button class="expand-btn" onclick="event.stopPropagation();toggleExpand(${realIdx},this)">${isExpanded?'▲':'▼'}</button>
      </div>
    </div>`;
  }).join('');
}

function renderHighPriority(alerts){
  const high=alerts.filter(a=>a.type==='drain'||a.type==='approval');
  document.getElementById('highCount').textContent=high.length;
  const feed=document.getElementById('highFeed');
  if(!high.length){
    feed.innerHTML=`<div class="empty-state" style="padding:2rem 1rem;"><div class="empty-icon" style="font-size:1.5rem;">🔍</div><div class="empty-text">No high-priority alerts</div></div>`;
    return;
  }
  feed.innerHTML=high.map(a=>{
    const idx=allAlerts.indexOf(a);
    return `<div class="activity-item" onclick="showModal(${idx})">
      <div class="alert-dot ${DOT[a.type]}" style="width:28px;height:28px;font-size:11px;">${ICONS[a.type]}</div>
      <div class="activity-line">
        <div class="activity-title">${a.title}</div>
        <div class="activity-addr">${a.detail}</div>
        <div class="activity-block">block ${a.block}</div>
      </div>
    </div>`;
  }).join('');
}

function showToast(a){
  if(a.type!=='drain'&&a.type!=='approval')return;
  const c=document.getElementById('toastContainer');
  const t=document.createElement('div');
  t.className=`toast ${a.type}`;
  t.innerHTML=`<div class="toast-title">${a.title}</div><div class="toast-detail">${a.detail}</div>`;
  c.prepend(t);
  setTimeout(()=>t.remove(),5000);
}

function clearAll(){
  if(!confirm('Clear all alerts?'))return;
  fetch('/api/clear',{method:'POST'}).then(()=>{
    allAlerts=[];
    expandedItems.clear();
    renderFeed();
    renderHighPriority([]);
    document.getElementById('sTokens').textContent='0';
    document.getElementById('sTransfers').textContent='0';
    document.getElementById('sDrains').textContent='0';
    document.getElementById('sApprovals').textContent='0';
  });
}

async function refresh(){
  try{
    const r=await fetch('/api/data');
    const d=await r.json();
    document.getElementById('sTokens').textContent=d.stats.tokens.toLocaleString();
    document.getElementById('sTransfers').textContent=d.stats.transfers.toLocaleString();
    document.getElementById('sDrains').textContent=d.stats.drains.toLocaleString();
    document.getElementById('sApprovals').textContent=d.stats.approvals.toLocaleString();
    const lb=d.alerts.length?d.alerts[0].block:'—';
    document.getElementById('blockBadge').textContent=`block ${lb}`;
    document.getElementById('lastUpdate').textContent=`Last update: ${new Date().toLocaleTimeString()}`;
    if(d.alerts.length>lastCount&&lastCount>0){
      d.alerts.slice(0,d.alerts.length-lastCount).forEach(showToast);
    }
    lastCount=d.alerts.length;
    allAlerts=d.alerts;
    renderFeed();
    renderHighPriority(d.alerts);
  }catch(e){console.log(e);}
}

refresh();
setInterval(refresh,5000);
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
    data["alerts"] = data["alerts"][:500]
    t = alert.get("type", "")
    if t == "drain": data["stats"]["drains"] += 1
    elif t == "approval": data["stats"]["approvals"] += 1
    elif t == "transfer": data["stats"]["transfers"] += 1
    data["stats"]["tokens"] = len(set(
        a["detail"].split("|")[-1].strip()
        for a in data["alerts"]
        if a.get("type") == "transfer" and "|" in a.get("detail", "")
    ))
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