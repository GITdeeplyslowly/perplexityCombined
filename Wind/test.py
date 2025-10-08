import requests
import json
import os
from logzero import logger
from login import login
from dotenv import load_dotenv

# ✅ Load environment variables from .env
load_dotenv()

# ✅ Load auth_token from file if available
def load_auth_token():
    if os.path.exists("auth_token.json"):
        with open("auth_token.json", "r") as file:
            data = json.load(file)
            return data.get("auth_token")
    return None

# ✅ Validate auth_token before making API requests
def validate_token(auth_token):
    test_url = "https://apiconnect.angelbroking.com/rest/secure/angelbroking/user/v1/getProfile"
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = requests.get(test_url, headers=headers)
    return response.status_code == 200

# ✅ Get auth_token (retry login if necessary)
auth_token = load_auth_token()
if not auth_token or not validate_token(auth_token):
    logger.warning("🔄 auth_token not found or invalid, logging in again...")
    smart_api, auth_token, refresh_token = login()
    if not auth_token:
        logger.error("❌ SmartAPI login failed. Check credentials.")
        exit()

# ✅ API Headers (Ensure API key is picked from .env)
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {auth_token.strip().replace('Bearer ', '')}",  # ✅ Fix duplicate "Bearer"
    "Accept": "application/json",
    "X-UserType": "USER",
    "X-SourceID": "WEB",
    "X-ClientLocalIP": "127.0.0.1",  # Replace if necessary
    "X-ClientPublicIP": "106.193.147.98",  # Replace if necessary
    "X-MACAddress": "3c:97:0e:8b:18:a0",  # Replace if necessary
    "X-PrivateKey": os.getenv("API_KEY")  # ✅ Pick API key dynamically from .env
}

# ✅ Step 1: Test API Connection with Profile API
profile_url = "https://apiconnect.angelbroking.com/rest/secure/angelbroking/user/v1/getProfile"
profile_response = requests.get(profile_url, headers=headers)

logger.info(f"🔎 Profile API Status Code: {profile_response.status_code}")
logger.info(f"🔎 Profile API Response: {profile_response.text}")

if profile_response.status_code != 200:
    logger.error("❌ Profile API request failed. Your session may be invalid.")
    exit()

# ✅ Step 2: Request Historical Data
url = "https://apiconnect.angelbroking.com/rest/secure/angelbroking/historical/candle"

params = {
    "exchange": "NSE",
    "symboltoken": "2885",
    "interval": "DAY",
    "fromdate": "2024-01-01 00:00",
    "todate": "2024-01-05 23:59"
}

logger.info(f"📡 Sending Request to: {url}")
logger.info(f"📩 Headers: {headers}")
logger.info(f"📊 Request Body: {params}")

response = requests.post(url, json=params, headers=headers)

# ✅ Print raw response before parsing
logger.info(f"📜 API Response Status Code: {response.status_code}")
logger.info(f"📜 API Response Text: {response.text}")

# ✅ Check if response is empty or an error page
if response.status_code != 200 or not response.text.strip() or "<html>" in response.text.lower():
    logger.error("❌ API request failed. Received an empty or invalid response.")
    exit()

# ✅ Try parsing JSON, handle errors
try:
    data = response.json()
    logger.info(f"📊 Parsed API Data: {data}")
except requests.exceptions.JSONDecodeError:
    logger.error("❌ Failed to parse API response. Response is not JSON.")
    exit()
