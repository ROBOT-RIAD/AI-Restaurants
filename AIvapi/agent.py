from .create_assistant import create_assistant
from .add_phone import create_phone_number
from rest_framework.response import Response

from django.conf import settings

VAPI_API_KEY=settings.VAPI_API

class AGENT:
    def __init__(self):        
        self.assistant_id = None
        self.phone_id = None
        self.org_id = None
        self.voice = None
        
        self.restaurant_name = None
        self.twillo_num = None
        self.ssid = None
        self.auth_token = None
        self.fallback = None
    
    # @property
    # def demo_link(self):
    #     return f"https://vapi.ai/?demo=true&shareKey={os.getenv('VAPI_PUBLIC_KEY')}&assistantId={self.assistant_id}"
    
    def __create_assistant(self, voice="matilda", restaurant_name="Garlic and Ginger", speed=1.0, webhook_url="https://7647f03079a0.ngrok-free.app/vapi-webhook", restaurant_fallback="+8801615791025"):
        try:
            response = create_assistant(voice=voice, restaurant_name=restaurant_name, speed=speed, webhook_url=webhook_url, restaurant_no=restaurant_fallback)
            
            return response
        except Exception as e:
            raise Exception(f"Failed to create assistant: {e}")
    
    def get_assistant_id(self):
        if not self.assistant_id:
            raise ValueError("Assistant ID is not set. Please create an assistant first.")
        return self.assistant_id
    
    def get_phone_id(self):
        if not self.phone_id:
            raise ValueError("Phone ID is not set. Please create a phone number first.")
        return self.phone_id
    
    def __create_number(self, twillo_num="", ssid="", restaurant_fallback="", auth_token="", assistant=""):        
        try:
            response = create_phone_number(
                name=self.restaurant_name, 
                twillo_num=twillo_num, 
                ssid=ssid, 
                restaurant_fallback=restaurant_fallback,
                auth_token=auth_token, 
                assistant=assistant)
            return response
        except Exception as e:
            raise Exception(f"Failed to create phone number: {e}")
            
    def create_agent(
        self,
        voice="matilda", 
        restaurant_name="Hamster and Cheese",
        speed=1.0,
        twillo_num="", 
        ssid="", 
        restaurant_fallback="", 
        auth_token="", 
        webhook="https://sacred-renewing-dove.ngrok-free.app/vapi-webhook/"
        ):
        
        if not voice and not self.voice:
            raise ValueError("Voice is required to create an agent.")
        if not restaurant_name and not self.restaurant_name:
            raise ValueError("Restaurant name is required to create an agent.")
        if not twillo_num and not self.twillo_num:
            raise ValueError("Twilio number is required to create an agent.")
        if not restaurant_fallback and not self.fallback:
            raise ValueError("Restaurant fallback number is required to create an agent.")
        if not ssid and not self.ssid:
            raise ValueError("Twilio Account SID is required to create an agent.")
        if not auth_token and not self.auth_token:
            raise ValueError("Twilio Auth Token is required to create an agent.")
        if not speed:
            speed = 1.0
        if not webhook:
            raise ValueError("Webhook URL is required to create an agent.")
        
        assistant_response = self.__create_assistant(
            voice=voice, 
            restaurant_name=restaurant_name, 
            speed=speed,
            webhook_url=webhook,
            restaurant_fallback=restaurant_fallback
            )
        if not assistant_response:
            raise Exception("Failed to create assistant.")
        
        
        self.restaurant_name = restaurant_name
        
        number_assignment = self.__create_number(
            twillo_num=twillo_num, 
            ssid=ssid, 
            assistant=assistant_response.get("id"),
            restaurant_fallback=restaurant_fallback, 
            auth_token=auth_token)
        if not number_assignment:
            raise Exception("Failed to create phone number.")
        
        try:  
            self.fallback = number_assignment['fallbackDestination'].get("number")
            self.phone_id = number_assignment.get("id")
            self.twillo_num = number_assignment.get("number")
            self.ssid = number_assignment.get('twilioAccountSid')
            self.auth_token = auth_token
            
            self.voice = assistant_response['voice'].get('voiceId')
            self.restaurant_name = assistant_response.get("name")
            self.assistant_id = assistant_response.get("id")
            self.org_id = assistant_response.get("orgId")
        except KeyError as e:
            self.fallback = None
            self.phone_id = None
            self.twillo_num = None
            self.ssid = None
            self.auth_token = None

            self.voice = None
            self.restaurant_name = None
            self.assistant_id = None
            self.org_id = None

            return Response(
                {"Number is already in use or missing key in response."},
                status=400
            )
            
            # raise Exception(f"Number is already in use or missing key in response: {e}")

        return [assistant_response, number_assignment]