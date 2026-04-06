from web3 import Web3
import requests
import time

ERC20_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"}
        ],
        "name": "Transfer",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "owner", "type": "address"},
            {"indexed": True, "name": "spender", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"}
        ],
        "name": "Approval",
        "type": "event"
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

TRANSFER_TOPIC = Web3.keccak(text="Transfer(address,address,uint256)").hex()
APPROVAL_TOPIC = Web3.keccak(text="Approval(address,address,uint256)").hex()

def send_telegram(token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")

def is_erc20(w3, address):
    """Check if a contract looks like an ERC20 token."""
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

def process_transfer(w3, log, tokens, bot_token, chat_id, threshold):
    address = log["address"]
    if address not in tokens:
        return
    symbol, decimals = tokens[address]
    divisor = 10 ** decimals
    try:
        from_addr = "0x" + log["topics"][1].hex()[-40:]
        to_addr   = "0x" + log["topics"][2].hex()[-40:]
        value     = int(log["data"].hex(), 16) / divisor
    except:
        return

    print(f"[Transfer] {value:.2f} {symbol} | {from_addr[:10]}... → {to_addr[:10]}... | Block {log['blockNumber']}")

    if value >= threshold:
        msg = (
            f"🚨 <b>DRAIN DETECTED</b>\n"
            f"Token:  <b>{symbol}</b> (<code>{address}</code>)\n"
            f"Amount: <b>{value:.2f} {symbol}</b>\n"
            f"From:   <code>{from_addr}</code>\n"
            f"To:     <code>{to_addr}</code>\n"
            f"Block:  {log['blockNumber']}"
        )
        send_telegram(bot_token, chat_id, msg)

def process_approval(w3, log, tokens, bot_token, chat_id):
    address = log["address"]
    if address not in tokens:
        return
    symbol, _ = tokens[address]
    try:
        owner   = "0x" + log["topics"][1].hex()[-40:]
        spender = "0x" + log["topics"][2].hex()[-40:]
        value   = int(log["data"].hex(), 16)
    except:
        return

    MAX_UINT256 = 2**256 - 1
    if value >= MAX_UINT256:
        print(f"[Approval] ⚠️  UNLIMITED approval | {owner[:10]}... → {spender[:10]}... | Block {log['blockNumber']}")
        msg = (
            f"⚠️ <b>UNLIMITED APPROVAL</b>\n"
            f"Token:   <b>{symbol}</b> (<code>{address}</code>)\n"
            f"Owner:   <code>{owner}</code>\n"
            f"Spender: <code>{spender}</code>\n"
            f"Amount:  MAX (unlimited)\n"
            f"Block:   {log['blockNumber']}"
        )
        send_telegram(bot_token, chat_id, msg)

def scan_for_new_tokens(w3, from_block, to_block, known_tokens):
    """Scan blocks for new contract deployments that look like ERC20 tokens."""
    found = {}
    try:
        for block_num in range(from_block, to_block + 1):
            block = w3.eth.get_block(block_num, full_transactions=True)
            for tx in block.transactions:
                # Contract creation = no 'to' address
                if tx["to"] is None:
                    receipt = w3.eth.get_transaction_receipt(tx["hash"])
                    contract_address = receipt.get("contractAddress")
                    if contract_address and contract_address not in known_tokens:
                        if is_erc20(w3, contract_address):
                            symbol, decimals = get_token_info(w3, contract_address)
                            found[contract_address] = (symbol, decimals)
                            print(f"🆕 New ERC20 detected: {symbol} at {contract_address}")
    except Exception as e:
        print(f"Token scan error: {e}")
    return found

def start_monitor(bot_token, chat_id, rpc_url, threshold):
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        print("❌ Cannot connect to node at", rpc_url)
        return

    from_block = w3.eth.block_number
    tokens = {}  # address -> (symbol, decimals)

    print(f"🤖 Auto-monitoring ALL ERC20 tokens on {rpc_url}")
    print(f"📦 Starting from block {from_block}")
    print(f"🚨 Alert threshold: {threshold} tokens")
    print("-" * 50)

    send_telegram(bot_token, chat_id,
        f"🟢 <b>Auto-Monitor Started</b>\n"
        f"Watching ALL new ERC20 deployments\n"
        f"Node: <code>{rpc_url}</code>\n"
        f"Threshold: {threshold} tokens\n"
        f"From block: {from_block}")

    while True:
        try:
            to_block = w3.eth.block_number

            if from_block > to_block:
                time.sleep(2)
                continue

            # Auto-discover new ERC20 tokens
            new_tokens = scan_for_new_tokens(w3, from_block, to_block, tokens)
            if new_tokens:
                tokens.update(new_tokens)
                for addr, (sym, dec) in new_tokens.items():
                    send_telegram(bot_token, chat_id,
                        f"🆕 <b>New ERC20 Token Detected!</b>\n"
                        f"Symbol: <b>{sym}</b>\n"
                        f"Address: <code>{addr}</code>\n"
                        f"Block: {to_block}")

            if tokens:
                token_addresses = list(tokens.keys())

                # Fetch Transfer events for all known tokens
                transfer_logs = w3.eth.get_logs({
                    "fromBlock": from_block,
                    "toBlock": to_block,
                    "address": token_addresses,
                    "topics": [TRANSFER_TOPIC]
                })
                for log in transfer_logs:
                    process_transfer(w3, log, tokens, bot_token, chat_id, threshold)

                # Fetch Approval events for all known tokens
                approval_logs = w3.eth.get_logs({
                    "fromBlock": from_block,
                    "toBlock": to_block,
                    "address": token_addresses,
                    "topics": [APPROVAL_TOPIC]
                })
                for log in approval_logs:
                    process_approval(w3, log, tokens, bot_token, chat_id)

            from_block = to_block + 1

        except Exception as e:
            print(f"⚠️  Error: {e}")
            time.sleep(2)

        time.sleep(2)
