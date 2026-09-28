import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

BOT_TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "dev-secret")
USE_POLLING = os.environ.get("USE_POLLING", "0") == "1"
PROMPT = (BASE_DIR / "prompt.txt").read_text(encoding="utf-8")
WEBAPP_URL = PUBLIC_URL  # мини-апп открывается с того же домена
