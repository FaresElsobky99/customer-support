import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
SUPPORT_POLICY_PATH = PROJECT_ROOT / "support_policy.txt"

load_dotenv(ENV_FILE)

DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing from .env")

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is missing from .env")
