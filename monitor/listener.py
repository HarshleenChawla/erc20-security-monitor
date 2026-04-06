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

def post_alert(alert_type, title, detail, block):
    try:
        requests.post(f"{DASHBOARD_URL}/api/alert", json={
            "type": alert_type,
            "title": title,
            "detail": detail,
            "block": block
        }, timeout=3)
    except Exception as e:
        print(f"Dashboard post error: {e}")

def send_telegram(token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")

def is_erc20(w3, address):
    try:
        contract = w3.eth.contract(address=address, abi=ERC20_ABI)
        contract.functions.totalSupply().call()
        contract.functions.decimals().call()
        contract.functions.symbol().call()
        return True
    except:
        return False

def get_token_info(w3, address):
    try:
        contract = w3.eth.contract(address=address, abi=ERC20_ABI)
        symbol = contract.functions.symbol().call()
        decimals = contract.functions.decimals().call()
        return symbol, decimals
    except:
        return "???", 18

def scan_for_new_tokens(w3, from_block, to_block, known_tokens):
    found = {}
    try:
        for block_num in range(from_block, to_block + 1):
            block = w3.eth.get_block(block_num, full_transactions=True)
            for tx in block.transactions:
                if tx["to"] is None:
                    receipt = w3.eth.get_transaction_receipt(tx["hash"])
                    contract_address = receipt.get("contractAddress")
                    if contract_address and contract_address not in known_tokens:
                        if is_erc20(w3, contract_address):
                            symbol, decimals = get_token_info(w3, contract_address)
                            found[contract_address] = (symbol, decimals)
                            print(f"New ERC20 detected: {symbol} at {contract_address}")
    except Exception as e:
        print(f"Token scan error: {e}")
    return found

def start_monitor(bot_token, chat_id, rpc_url, threshold):
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print("Cannot connect to node at", rpc_url)
        return

    from_block = w3.eth.block_number
    tokens = {}

    print(f"Auto-monitoring ALL ERC20 tokens on {rpc_url}")
    print(f"Starting from block {from_block}")
    print(f"Alert threshold: {threshold} tokens")
    print("-" * 50)

    send_telegram(bot_token, chat_id,
        f"Auto-Monitor Started\nWatching ALL new ERC20 deployments\nNode: {rpc_url}\nThreshold: {threshold} tokens\nFrom block: {from_block}")

    post_alert("start", "Monitor started", f"Watching mainnet from block {from_block}", from_block)

    while True:
        try:
            to_block = w3.eth.block_number
            if from_block > to_block:
                time.sleep(2)
                continue

            new_tokens = scan_for_new_tokens(w3, from_block, to_block, tokens)
            if new_tokens:
                tokens.update(new_tokens)
                for addr, (sym, dec) in new_tokens.items():
                    msg = f"New ERC20 Token Detected!\nSymbol: {sym}\nAddress: {addr}\nBlock: {to_block}"
                    send_telegram(bot_token, chat_id, msg)
                    post_alert("token", f"New token: {sym}", addr, to_block)

            if tokens:
                token_addresses = list(tokens.keys())

                transfer_logs = w3.eth.get_logs({
                    "fromBlock": from_block,
                    "toBlock": to_block,
                    "address": token_addresses,
                    "topics": [TRANSFER_TOPIC]
                })
                for log in transfer_logs:
                    address = log["address"]
                    sym, decimals = tokens.get(address, ("???", 18))
                    divisor = 10 ** decimals
                    try:
                        from_addr = "0x" + log["topics"][1].hex()[-40:]
                        to_addr = "0x" + log["topics"][2].hex()[-40:]
                        value = int(log["data"].hex(), 16) / divisor
                    except:
                        continue

                    print(f"[Transfer] {value:.2f} {sym} | {from_addr[:10]}... → {to_addr[:10]}... | Block {log['blockNumber']}")
                    post_alert("transfer", f"Transfer: {value:.0f} {sym}", f"{from_addr[:12]}... → {to_addr[:12]}...", log['blockNumber'])

                    if value >= threshold:
                        msg = (f"DRAIN DETECTED\nToken: {sym} ({address})\n"
                               f"Amount: {value:.2f} {sym}\nFrom: {from_addr}\nTo: {to_addr}\nBlock: {log['blockNumber']}")
                        send_telegram(bot_token, chat_id, msg)
                        post_alert("drain", f"Drain: {value:.0f} {sym}", f"{from_addr[:12]}... → {to_addr[:12]}...", log['blockNumber'])

                approval_logs = w3.eth.get_logs({
                    "fromBlock": from_block,
                    "toBlock": to_block,
                    "address": token_addresses,
                    "topics": [APPROVAL_TOPIC]
                })
                for log in approval_logs:
                    address = log["address"]
                    sym, _ = tokens.get(address, ("???", 18))
                    try:
                        owner = "0x" + log["topics"][1].hex()[-40:]
                        spender = "0x" + log["topics"][2].hex()[-40:]
                        value = int(log["data"].hex(), 16)
                    except:
                        continue

                    MAX_UINT256 = 2**256 - 1
                    if value >= MAX_UINT256:
                        print(f"[Approval] UNLIMITED | {owner[:10]}... → {spender[:10]}...")
                        msg = (f"UNLIMITED APPROVAL\nToken: {sym} ({address})\n"
                               f"Owner: {owner}\nSpender: {spender}\nAmount: MAX\nBlock: {log['blockNumber']}")
                        send_telegram(bot_token, chat_id, msg)
                        post_alert("approval", f"Unlimited approval: {sym}", f"{owner[:12]}... → {spender[:12]}...", log['blockNumber'])

            from_block = to_block + 1

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)

        time.sleep(2)
