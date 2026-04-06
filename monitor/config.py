import os
from dotenv import load_dotenv
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")
RPC_URL            = os.getenv("RPC_URL")
DRAIN_THRESHOLD    = float(os.getenv("DRAIN_THRESHOLD", "100000"))
