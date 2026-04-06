import time, requests
from web3 import Web3

# ── CONFIG ──────────────────────────────────────────────
ALCHEMY_URL   = "https://eth-mainnet.g.alchemy.com/v2/pSU5J2i4mTXevw_PfV9DQ"
DASHBOARD_URL = "http://127.0.0.1:8080/api/alert"
THRESHOLD     = 100_000   # tokens (human-readable, NOT raw)
START_BLOCK   = "latest"
# ────────────────────────────────────────────────────────

w3 = Web3(Web3.HTTPProvider(ALCHEMY_URL))

TRANSFER_TOPIC = w3.keccak(text="Transfer(address,address,uint256)").hex()
APPROVAL_TOPIC = w3.keccak(text="Approval(address,address,uint256)").hex()
MAX_UINT256    = 2**256 - 1

# Cache token decimals so we don't re-fetch every time
decimals_cache = {}

ERC20_ABI = [
    {"inputs":[],"name":"decimals","outputs":[{"type":"uint8"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"symbol","outputs":[{"type":"string"}],"stateMutability":"view","type":"function"},
]

def get_token_info(address):
    if address in decimals_cache:
        return decimals_cache[address]
    try:
        contract = w3.eth.contract(address=Web3.to_checksum_address(address), abi=ERC20_ABI)
        symbol   = contract.functions.symbol().call()
        decimals = contract.functions.decimals().call()
        decimals_cache[address] = (symbol, decimals)
        return symbol, decimals
    except:
        decimals_cache[address] = ("???", 18)
        return "???", 18

def post_alert(alert):
    try:
        requests.post(DASHBOARD_URL, json=alert, timeout=3)
        print(f"  ✅ Alert posted: {alert['title']}")
    except Exception as e:
        print(f"  ❌ Failed to post alert: {e}")

def shorten(addr):
    return f"{addr[:6]}...{addr[-4:]}"

def scan():
    current = w3.eth.block_number if START_BLOCK == "latest" else START_BLOCK
    print(f"🔍 Starting scan from block {current}")
    print(f"⚠️  Alert threshold: {THRESHOLD:,} tokens\n")

    while True:
        try:
            latest = w3.eth.block_number

            if current > latest:
                time.sleep(5)
                continue

            print(f"📦 Scanning block {current} / {latest}")

            logs = w3.eth.get_logs({
                "fromBlock": current,
                "toBlock":   current,
                "topics":    [[TRANSFER_TOPIC, APPROVAL_TOPIC]]
            })

            for log in logs:
                topic0   = log["topics"][0].hex()
                contract = log["address"]

                # ── TRANSFER ──────────────────────────────
                if topic0 == TRANSFER_TOPIC and len(log["topics"]) >= 3:
                    symbol, decimals = get_token_info(contract)
                    raw_amount = int(log["data"].hex(), 16) if log["data"] else 0
                    amount     = raw_amount / (10 ** decimals)   # ← THIS was the bug

                    from_addr = "0x" + log["topics"][1].hex()[-40:]
                    to_addr   = "0x" + log["topics"][2].hex()[-40:]

                    # Post ALL transfers as "transfer" type
                    post_alert({
                        "type":   "transfer",
                        "title":  f"{symbol} Transfer: {amount:,.2f} tokens",
                        "detail": f"{shorten(from_addr)} → {shorten(to_addr)} | {contract}",
                        "block":  current,
                    })

                    # If above threshold → also post as drain alert
                    if amount >= THRESHOLD:
                        post_alert({
                            "type":   "drain",
                            "title":  f"🚨 DRAIN: {amount:,.0f} {symbol}",
                            "detail": f"From {shorten(from_addr)} → {shorten(to_addr)}",
                            "block":  current,
                        })

                # ── APPROVAL ──────────────────────────────
                elif topic0 == APPROVAL_TOPIC and len(log["topics"]) >= 3:
                    symbol, decimals = get_token_info(contract)
                    raw_amount = int(log["data"].hex(), 16) if log["data"] else 0

                    if raw_amount == MAX_UINT256:
                        owner   = "0x" + log["topics"][1].hex()[-40:]
                        spender = "0x" + log["topics"][2].hex()[-40:]
                        post_alert({
                            "type":   "approval",
                            "title":  f"⚠️ Unlimited Approval: {symbol}",
                            "detail": f"{shorten(owner)} → spender {shorten(spender)}",
                            "block":  current,
                        })

            current += 1
            time.sleep(0.5)   # be gentle with the RPC

        except Exception as e:
            print(f"❌ Error on block {current}: {e}")
            time.sleep(3)

if __name__ == "__main__":
    scan()
