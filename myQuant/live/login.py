"""
live/login.py

SmartAPI login and session management for the unified trading system.

- Handles API key, client code, PIN, TOTP for Angel One session creation.
- Provides method for authenticated SmartConnect client (for streaming/tick data).
- Designed for GUI- or CLI-driven login with explicit user control and safety.
- Saves and loads session tokens from disk to avoid repeated logins.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional

try:
    from SmartApi import SmartConnect
except ImportError:
    SmartConnect = None
    logging.warning("SmartAPI client not installed. install with `pip install smartapi-python`.")

try:
    import pyotp
except ImportError:
    pyotp = None
    logging.warning("pyotp not installed. Install with `pip install pyotp` for dynamic TOTP generation.")

SESSION_FILE = r"C:\Users\user\projects\angelalgo\auth_token.json"

class SmartAPISessionManager:
    def __init__(self, api_key: str, client_code: str, pin: str, totp_secret: str):
        self.api_key = api_key
        self.client_code = client_code
        self.pin = pin
        self.totp_secret = totp_secret  # Store TOTP secret for dynamic generation
        self.session = None
        self.session_info = {}
        if SmartConnect is None:
            raise ImportError("SmartAPI client is not installed.")
        if pyotp is None:
            raise ImportError("pyotp is not installed. Install with `pip install pyotp` for TOTP generation.")

    def login(self) -> dict:
        """
        Authenticate with SmartAPI, save JWT and feed token to SESSION_FILE.
        Returns:
            dict with tokens, may raise Exception on auth failure
        """
        smartapi = SmartConnect(api_key=self.api_key)
        try:
            # Generate fresh TOTP token using the secret
            fresh_totp = pyotp.TOTP(self.totp_secret).now()
            logging.info(f"Generated fresh TOTP for authentication")
            
            res = smartapi.generateSession(self.client_code, self.pin, fresh_totp)
            jwt_token = res["data"]["jwtToken"]
            feed_token = smartapi.getfeedToken()
            profile = smartapi.getProfile(self.client_code)["data"]
            self.session_info = {
                "jwt_token": jwt_token,
                "feed_token": feed_token,
                "client_code": self.client_code,
                "refresh_time": datetime.now().isoformat(),
                "profile": profile,
            }
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump({"data": {"auth_token": jwt_token, "client_id": self.client_code}}, f)
            logging.info(f"SmartAPI login successful for {self.client_code}. Session token saved.")
            self.session = smartapi
            return self.session_info
        except Exception as e:
            logging.error(f"SmartAPI login failed: {e}")
            raise

    def load_session_from_file(self) -> Optional[dict]:
        """
        Loads session tokens from local file if available.
        """
        if not os.path.exists(SESSION_FILE):
            logging.warning("No session token file found.")
            return None
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            token_data = json.load(f)
            if "data" in token_data:
                # Convert Wind format to myQuant format
                self.session_info = {
                    "jwt_token": token_data["data"]["auth_token"],
                    "feed_token": None,
                    "client_code": token_data["data"]["client_id"]
                }
            else:
                self.session_info = token_data
        logging.info(f"Loaded SmartAPI session from file (client {self.session_info.get('client_code')}).")
        return self.session_info

    def is_session_valid(self) -> bool:
        """Simple Wind-style token validation with API test."""
        if not self.session_info or not self.session_info.get("jwt_token"):
            return False
            
        try:
            import requests
            test_url = "https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getProfile"
            headers = {"Authorization": f"Bearer {self.session_info['jwt_token']}"}
            response = requests.get(test_url, headers=headers)
            return response.status_code == 200
        except Exception:
            return False
    
    def load_session(self) -> Optional[dict]:
        """
        Load and validate session using Wind's robust approach.
        Returns session info if valid, None if invalid/expired.
        """
        session_info = self.load_session_from_file()
        if session_info and self.is_session_valid():
            return session_info
        return None

    def get_smartconnect(self):
        """
        Public API to get SmartConnect object with valid session.
        """
        if self.session is not None:
            return self.session
        elif self.load_session_from_file() and self.is_session_valid():
            smartapi = SmartConnect(api_key=self.api_key)
            smartapi.feed_token = self.session_info["feed_token"]
            self.session = smartapi
            return smartapi
        else:
            self.login()
            return self.session

# CLI entry point for manual login and session check
if __name__ == "__main__":
    import getpass
    print("SmartAPI Login Utility for Unified Trading System")
    api_key = input("API Key: ").strip()
    client_code = input("Client Code: ").strip()
    pin = getpass.getpass("PIN: ")
    totp_token = getpass.getpass("TOTP Token: ")
    mgr = SmartAPISessionManager(api_key, client_code, pin, totp_token)
    try:
        info = mgr.login()
        print("Login successful. Session token saved.")
        print(f"Feed Token: {info['feed_token']}")
        print(f"JWT Token: (hidden)")
    except Exception as e:
        print(f"Login failed: {e}")
