import os
import time

import requests
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://127.0.0.1:8080/api/alert")
THRESHOLD = float(os.getenv("DRAIN_THRESHOLD", "100000"))
START_BLOCK = os.getenv("START_BLOCK", "latest")

w3 = Web3(Web3.HTTPProvider(RPC_URL))

TRANSFER_TOPIC = w3.keccak(text="Transfer(address,address,uint256)").hex()
APPROVAL_TOPIC = w3.keccak(text="Approval(address,address,uint256)").hex()
MAX_UINT256 = 2**256 - 1
token_cache = {}

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


def get_token_info(address):
    if address in token_cache:
        return token_cache[address]

    try:
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(address),
            abi=ERC20_ABI,
        )
        symbol = contract.functions.symbol().call()
        decimals = contract.functions.decimals().call()
        token_cache[address] = (symbol, decimals)
        return symbol, decimals
    except Exception:
        token_cache[address] = ("???", 18)
        return "???", 18


def post_alert(alert):
    try:
        response = requests.post(DASHBOARD_URL, json=alert, timeout=5)
        if response.ok:
            print(f"POSTED {alert['type']} | {alert['title']} [{response.status_code}]")
        else:
            print(f"POST FAILED {response.status_code} | {response.text[:200]}")
    except Exception as e:
        print(f"POST ERROR: {e}")


def scan():
    if not w3.is_connected():
        print(f"Cannot connect to RPC_URL: {RPC_URL}")
        return

    current = w3.eth.block_number if START_BLOCK == "latest" else int(START_BLOCK)

    print("=================================")
    print("  ERC-20 Mainnet Security Monitor")
    print("=================================")
    print(f"RPC: {RPC_URL}")
    print(f"Dashboard: {DASHBOARD_URL}")
    print(f"Starting from block {current}")
    print(f"Drain threshold: {THRESHOLD:,.0f} tokens")
    print("-" * 50)

    post_alert({
        "type": "start",
        "title": "Monitor Started",
        "detail": f"Scanning from block {current} | threshold {THRESHOLD:,.0f} tokens",
        "block": current,
    })

    while True:
        try:
            latest = w3.eth.block_number
            if current > latest:
                time.sleep(3)
                continue

            print(f"Scanning block {current} / {latest}")

            logs = w3.eth.get_logs({
                "fromBlock": current,
                "toBlock": current,
                "topics": [[TRANSFER_TOPIC, APPROVAL_TOPIC]],
            })

            for log in logs:
                topic0 = log["topics"][0].hex()
                contract = log["address"]

                if topic0 == TRANSFER_TOPIC and len(log["topics"]) >= 3:
                    symbol, decimals = get_token_info(contract)
                    raw_amount = int(log["data"].hex(), 16) if log["data"] else 0
                    amount = raw_amount / (10 ** decimals)
                    from_addr = "0x" + log["topics"][1].hex()[-40:]
                    to_addr = "0x" + log["topics"][2].hex()[-40:]

                    post_alert({
                        "type": "transfer",
                        "title": f"{symbol} Transfer: {amount:,.2f} tokens",
                        "detail": f"{from_addr} → {to_addr} | {contract}",
                        "block": current,
                    })

                    if amount >= THRESHOLD:
                        post_alert({
                            "type": "drain",
                            "title": f"DRAIN: {amount:,.0f} {symbol}",
                            "detail": f"{from_addr} → {to_addr} | {contract}",
                            "block": current,
                        })

                elif topic0 == APPROVAL_TOPIC and len(log["topics"]) >= 3:
                    symbol, _ = get_token_info(contract)
                    raw_amount = int(log["data"].hex(), 16) if log["data"] else 0

                    if raw_amount == MAX_UINT256:
                        owner = "0x" + log["topics"][1].hex()[-40:]
                        spender = "0x" + log["topics"][2].hex()[-40:]

                        post_alert({
                            "type": "approval",
                            "title": f"Unlimited Approval: {symbol}",
                            "detail": f"{owner} → {spender} | {contract}",
                            "block": current,
                        })

            current += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"Monitor error on block {current}: {e}")
            time.sleep(3)


if __name__ == "__main__":
    scan()
