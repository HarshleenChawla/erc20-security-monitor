import os
from dotenv import load_dotenv
load_dotenv()

RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")
DRAIN_THRESHOLD = float(os.getenv("DRAIN_THRESHOLD", "100000"))
