import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "BE"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# BE/config.py validates these at import time for normal processes. The smoke
# tests exercise pure utilities only, so placeholder values are enough.
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC00000000000000000000000000000000")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test-twilio-token")
