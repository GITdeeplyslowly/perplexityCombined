import os

# Load environment variables (already set in login.py)
API_KEY = os.getenv("API_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")
PASSWORD = os.getenv("PASSWORD")
TOTP_SECRET = os.getenv("SMARTAPI_TOTP_SECRET")
