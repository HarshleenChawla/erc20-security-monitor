import time
from monitor.config import RPC_URL, DRAIN_THRESHOLD
from monitor.listener import start_monitor

print("=================================")
print("  ERC-20 Mainnet Security Monitor")
print("  Auto-detecting all tokens...")
print("=================================")

while True:
    try:
        start_monitor(None, None, RPC_URL, DRAIN_THRESHOLD)
    except Exception as e:
        print(f"Monitor crashed: {e} — restarting in 10s...")
        time.sleep(10)
