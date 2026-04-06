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

HTML = '''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>ERC-20 Security Monitor</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, sans-serif; background: #0f1117; color: #e2e8f0; min-height: 100vh; padding: 2rem; }
h1 { font-size: 1.4rem; font-weight: 600; margin-bottom: 0.25rem; }
.sub { font-size: 0.8rem; color: #94a3b8; margin-bottom: 2rem; display: flex; align-items: center; gap: 6px; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: #22c55e; display: inline-block; animation: pulse 2s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
.grid-4 { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 1.5rem; }
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
.badge { display: inline-block; font-size: 11px; padding: 3px 10px; border-radius: 20px; font-weight: 500; background: #1a3b2a; color: #22c55e; }
@media(max-width:700px){ .grid-4{grid-template-columns:repeat(2,1fr);} .grid-2{grid-template-columns:1fr;} }
</style>
</head>
<body>
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;">
  <div>
    <h1>ERC-20 Security Monitor</h1>
    <div class="sub"><span class="dot"></span> Live · Ethereum Mainnet · auto-refreshes every 5s</div>
  </div>
  <span class="badge">System active</span>
</div>
<div class="grid-4">
  <div class="metric"><div class="label">Tokens found</div><div class="value" id="t" style="color:#3b82f6;">0</div><div class="vsub">auto-discovered</div></div>
  <div class="metric"><div class="label">Transfers seen</div><div class="value" id="tr">0</div><div class="vsub">since start</div></div>
  <div class="metric"><div class="label">Drain alerts</div><div class="value" id="d" style="color:#ef4444;">0</div><div class="vsub">large transfers</div></div>
  <div class="metric"><div class="label">Unlimited approvals</div><div class="value" id="a" style="color:#f59e0b;">0</div><div class="vsub">MAX_UINT256</div></div>
</div>
<div class="grid-2">
  <div class="card"><div class="card-title">Live alert feed</div><div id="feed"><div class="empty">Waiting for events...</div></div></div>
  <div class="card"><div class="card-title">Telegram preview</div><div id="tg"><div class="empty">No alerts yet...</div></div></div>
</div>
<script>
const icons={token:"N",drain:"D",approval:"!",start:"+"};
const colors={token:"#1e3a5f",drain:"#3b1a1a",approval:"#3b2e00",start:"#1a3b2a"};
async function refresh(){
  try{
    const r=await fetch("/api/data");
    const d=await r.json();
    document.getElementById("t").textContent=d.stats.tokens;
    document.getElementById("tr").textContent=d.stats.transfers.toLocaleString();
    document.getElementById("d").textContent=d.stats.drains;
    document.getElementById("a").textContent=d.stats.approvals;
    const feed=document.getElementById("feed");
    const tg=document.getElementById("tg");
    if(!d.alerts.length){
      feed.innerHTML="<div class='empty'>Waiting for events...</div>";
      tg.innerHTML="<div class='empty'>No alerts yet...</div>";
      return;
    }
    feed.innerHTML=d.alerts.slice(0,8).map(a=>`
      <div class="alert-row">
        <div class="alert-icon" style="background:${colors[a.type]||'#2d3748'}">${icons[a.type]||"?"}</div>
        <div class="alert-body"><div class="alert-title">${a.title}</div><div class="alert-detail">${a.detail}</div></div>
        <div class="alert-block">block ${a.block}</div>
      </div>`).join("");
    tg.innerHTML=d.alerts.filter(a=>a.type!=="transfer").slice(0,4).map(a=>`
      <div class="tg-bubble ${a.type}"><strong>${a.title}</strong><br><span class="mono">${a.detail}</span></div>`).join("");
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
    data["alerts"] = data["alerts"][:50]
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
