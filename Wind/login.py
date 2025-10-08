import os
import json
import pyotp
from dotenv import load_dotenv
from SmartApi import SmartConnect
from logzero import logger

def login():
    """Login to SmartAPI using trading mode by default"""
    try:
        # Set path for angelalgo directory
        ANGELALGO_PATH = r"C:\Users\user\projects\angelalgo"

        # Load trading environment by default
        env_path = os.path.join(ANGELALGO_PATH, ".env.trading")
        if not load_dotenv(env_path):
            logger.error(f"Failed to load {env_path}")
            return None, None, None

        print(f"✅ .env.trading loaded successfully!")

        # Get environment variables
        API_KEY = os.getenv("API_KEY")
        CLIENT_ID = os.getenv("CLIENT_ID")
        PASSWORD = os.getenv("PASSWORD")
        TOTP_SECRET = os.getenv("SMARTAPI_TOTP_SECRET")

        logger.debug(f"API_KEY: {API_KEY[:4]}*** (masked)")
        logger.debug(f"CLIENT_ID: {CLIENT_ID}")
        logger.debug(f"PASSWORD: *** (masked)")
        logger.debug(f"TOTP_SECRET: *** (masked)")

        if not all([API_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET]):
            logger.error("Missing required environment variables!")
            return None, None, None

        # Generate TOTP
        totp = pyotp.TOTP(TOTP_SECRET).now()
        logger.debug(f"Generated TOTP: {totp}")

        # Initialize and connect
        smart_api = SmartConnect(api_key=API_KEY)
        logger.debug(f"Calling generateSession with CLIENT_ID: {CLIENT_ID}, PASSWORD: *** (masked), TOTP: *** (masked)")
        response = smart_api.generateSession(CLIENT_ID, PASSWORD, totp)
        logger.debug(f"SmartAPI generateSession response: {response}")

        if response["status"]:
            auth_token = response["data"]["jwtToken"]
            refresh_token = response["data"]["refreshToken"]

            # Write token and client id to auth_token.json
            token_path = os.path.join(ANGELALGO_PATH, "auth_token.json")
            with open(token_path, "w") as file:
                json.dump({"data": {"auth_token": auth_token, "client_id": CLIENT_ID}}, file)
            print(f"Auth token written to: {token_path}")

            logger.info("✅ Login Successful!")
            return smart_api, auth_token, refresh_token
        else:
            logger.error(f"❌ Login Failed: {response}")
            return None, None, None
    except Exception as e:
        logger.exception(f"Login error: {e}")
        return None, None, None

if __name__ == "__main__":
    smart_api, auth_token, refresh_token = login()
    if smart_api:
        print("✅ SmartAPI Login Successful!")
    else:
        print("❌ SmartAPI Login Failed.")
