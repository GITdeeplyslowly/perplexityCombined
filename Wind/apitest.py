import requests
from login import login

smart_api, auth_token, refresh_token = login()

profile_url = "https://apiconnect.angelbroking.com/rest/secure/angelbroking/user/v1/getProfile"
headers = {"Authorization": f"Bearer {auth_token}"}

response = requests.get(profile_url, headers=headers)
print(f"Profile API Response: {response.text}")
