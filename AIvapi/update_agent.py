import requests
from django.conf import settings

VAPI_API_KEY=settings.VAPI_API



class UpdateAgent:
    def __init__(self, 
                 agent_id:str,
                 phone_id:str
                 ):
        self.api_key = VAPI_API_KEY
        if not self.api_key:
            raise ValueError("VAPI_API_KEY is not set in the environment variables.")
        
        self.agent_id = agent_id
        self.voice = None
        self.phone_id = phone_id

    def update_voiceId(self, speed:float, voice_id:str="matilda"):
        try:
            if speed == None:            
                response = requests.post(
                "https://api.vapi.ai/assistant/" + self.agent_id,
                headers={
                    "Authorization": "Bearer " + self.api_key
                },
                json={
                    "voice": {
                    "provider": "11labs",
                    "voiceId": voice_id,
                    "model": "eleven_multilingual_v2",
                    }
                },
                )

                if response.status_code == 201 or response.status_code == 200:
                    self.voice = voice_id

                return response.json()
                    
            else:
                if speed<0.7:
                    speed = 0.7
                elif speed>1.2:
                    speed = 1.2
                
                response = requests.post(
                "https://api.vapi.ai/assistant",
                headers={
                    "Authorization": "Bearer " + self.api_key
                },
                json={
                    "voice": {
                    "provider": "11labs",
                    "voiceId": voice_id,
                    "model": "eleven_multilingual_v2",
                    "speed": speed
                    }
                },
                )

                if response.status_code == 201 or response.status_code == 200:
                    self.voice = voice_id

                return response.json()
            
        except Exception as e:
            raise Exception(f"An error occurred while updating the voice ID: {e}")
        
        
    def update_restaurant_no(
        self,
        updated_fallback       
       ):
        try:
            response = requests.patch(
            "https://api.vapi.ai/phone-number/"+ self.phone_id,
            headers={
                "Authorization": "Bearer " + self.api_key
            },
            json={
                # "provider": "twilio",
                "fallbackDestination": {
                "type": "number",
                "number": updated_fallback
                }
            },
            )
            
            if response.status_code == 200:
                self.fallback = updated_fallback
            return response.json()

        except Exception as e:
            raise Exception(f"Failed to update restaurant fallback number: {e}")
        
    def update_twilio_creds(
        self,
        updated_twilio_number,
        updated_sid,
        updated_auth_token       
       ):
        try:
            response = requests.patch(
            "https://api.vapi.ai/phone-number/"+ self.phone_id,
            headers={
                "Authorization": "Bearer " + self.api_key
            },
            json={
                # "provider": "twilio",
                "number": updated_twilio_number,
                "twilioAuthToken": updated_auth_token,
                "twilioAccountSid": updated_sid
            },
            )
            
            if response.status_code == 200:
                self.ssid = updated_sid
                self.auth_token = updated_auth_token
                self.twilio_num = updated_twilio_number
            return response.json()

        except Exception as e:
            raise Exception(f"Failed to update Twilio credentials: {e}")




