import requests
from django.conf import settings

VAPI_API_KEY=settings.VAPI_API

def create_phone_number(name="Restaurant", twillo_num="", ssid="", restaurant_fallback="", auth_token="", assistant=""):
    try:
        # Create Phone Number (POST /phone-number)
        response = requests.post(
        "https://api.vapi.ai/phone-number",
        headers={
            "Authorization": f"Bearer {VAPI_API_KEY}"
        },
        json={
            "provider": "twilio",
            "number": twillo_num,
            "twilioAccountSid": ssid,
            "name": name,
            "assistantId": assistant,
            "twilioAuthToken": auth_token,
            "smsEnabled": True,
            "fallbackDestination": {
            "type": "number",
            "number": restaurant_fallback
            }
        },
        )
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to create phone number: {e}")