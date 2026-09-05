"""
Configuration settings for AgentTrust.
Loads environment variables from .env with fallback defaults.
"""
import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "AgentTrust").strip()
HOST = os.getenv("HOST", "0.0.0.0").strip()
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "True").strip().lower() in ("true", "1", "t")

# SQLite Database path
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agenttrust.db").strip()

# Razorpay Test Mode Credentials
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "").strip()

# Anthropic Claude API Key & Optional Workspace ID
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_WORKSPACE_ID = os.getenv("ANTHROPIC_WORKSPACE_ID", "").strip()

# Clerk Authentication (used to verify merchant session tokens on every API call)
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "").strip()
