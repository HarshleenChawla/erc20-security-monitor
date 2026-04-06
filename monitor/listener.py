from web3 import Web3
import requests
import time
import os

ERC20_ABI = [
    {"anonymous":False,"inputs":[{"indexed":True,"name":"from","type":"address"},{"indexed":True,"name":"to","type":"address"},{"indexed":False,"name":"value","type":"uint256"}],"name":"Transfer","type":"event"},
    {"anonymous":False,"inputs":[{"indexed":True,"name":"owner","type":"address"},{"indexed":True,"name":"spender","type":"address"},{"indexed":False,"name":"value","type":"uint256"}],"name":"Approval","type":"event"},
    {"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]

TRANSFER_TOPIC = Web3.keccak(text="Transfer(address,address,uint256)").hex()
APPROVAL_TOPIC = Web3.keccak(text="Approval(address,address,uint256)").hex()
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:8080")

def post(alert_type, title, detail, block):
    try:
        requests.post(f"{DASHBOARD_URL}/api/alert", json={
            "type": alert_type, "title": title, "detail": detail, "block": block
        }, timeout=3)
    except:
        pass

def is_erc20(w3, address):
    try:
        c = w3.eth.contract(address=address, abi=ERC20_ABI)
        c.functions.totalSupply().call()
        c.functions.decimals().call()
        c.functions.symbol().call()
        return True
    except:
        return False

def get_token_info(w3, address):
    try:
        c = w3.eth.contract(address=address, abi=ERC20_ABI)
        return c.functions.symbol().call(), c.functions.decimals().call()
    except:
        return "???", 18

def scan_new_tokens(w3, from_block, to_block, known_tokens):
    found = {}
    try:
        for bn in range(from_block, to_block + 1):
            block = w3.eth.get_block(bn, full_transactions=True)
            for tx in block.transactions:
                if tx["to"] is None:
                    receipt = w3.eth.get_transaction_receipt(tx["hash"])
                    addr = receipt.get("contractAddress")
                    if addr and addr not in known_tokens and is_erc20(w3, addr):
                        sym, dec = get_token_info(w3, addr)
                        found[addr] = (sym, dec)
                        print(f"New ERC20: {sym} at {addr}")
    except Exception as e:
        print(f"Scan error: {e}")
    return found

def start_monitor(bot_token, chat_id, rpc_url, threshold):
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print("Cannot connect to", rpc_url)
        return

    from_block = w3.eth.block_number
    tokens = {}

    print(f"Auto-monitoring ALL ERC20 tokens on {rpc_url}")
    print(f"Starting from block {from_block}")
    print(f"Alert threshold: {threshold} tokens")
    print("-" * 50)

    post("start", "Monitor started", f"Mainnet · from block {from_block}", from_block)

    while True:
        try:
            to_block = w3.eth.block_number
            if from_block > to_block:
                time.sleep(2)
                continue

            new_tokens = scan_new_tokens(w3, from_block, to_block, tokens)
            for addr, (sym, dec) in new_tokens.items():
                tokens[addr] = (sym, dec)
                post("token", f"New token: {sym}", addr, to_block)

            if tokens:
                addrs = list(tokens.keys())

                for log in w3.eth.get_logs({"fromBlock": from_block, "toBlock": to_block, "address": addrs, "topics": [TRANSFER_TOPIC]}):
                    sym, dec = tokens.get(log["address"], ("???", 18))
                    try:
                        fa = "0x" + log["topics"][1].hex()[-40:]
                        ta = "0x" + log["topics"][2].hex()[-40:]
                        val = int(log["data"].hex(), 16) / (10 ** dec)
                    except:
                        continue
                    print(f"[Transfer] {val:.2f} {sym} | block {log['blockNumber']}")
                    post("transfer", f"Transfer: {val:.0f} {sym}", f"{fa[:12]}...→{ta[:12]}...", log['blockNumber'])
                    if val >= threshold:
                        post("drain", f"DRAIN: {val:.0f} {sym}", f"{fa[:12]}...→{ta[:12]}...", log['blockNumber'])

                for log in w3.eth.get_logs({"fromBlock": from_block, "toBlock": to_block, "address": addrs, "topics": [APPROVAL_TOPIC]}):
                    sym, _ = tokens.get(log["address"], ("???", 18))
                    try:
                        owner = "0x" + log["topics"][1].hex()[-40:]
                        spender = "0x" + log["topics"][2].hex()[-40:]
                        val = int(log["data"].hex(), 16)
                    except:
                        continue
                    if val >= 2**256 - 1:
                        print(f"[Approval] UNLIMITED | {owner[:10]}...")
                        post("approval", f"Unlimited approval: {sym}", f"{owner[:12]}...→{spender[:12]}...", log['blockNumber'])

            from_block = to_block + 1

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)

        time.sleep(2)
