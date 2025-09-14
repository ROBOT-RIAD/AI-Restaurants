from django.conf import settings
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import AssistanceCreateSerializer
from restaurants.models import Restaurant
from .models import Assistance
import requests
from rest_framework import status
import re

VAPI_API = settings.VAPI_API

CREATE_ASSISTANT = "https://api.vapi.ai/assistant"
CREATE_PHONE = "https://api.vapi.ai/phone-number"
CREATE_TOOL = "https://api.vapi.ai/tool"
UPDATE_NUMBER = "https://api.vapi.ai/phone-number"
UPDATE_TOOL = "https://api.vapi.ai/tool"

# Create your views here.

def sanitize_name(restaurant_name):
    sanitized_name = re.sub(r'[^a-zA-Z0-9_-]', '_', restaurant_name)
    return sanitized_name




class AssistantCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self , request):
        serializer = AssistanceCreateSerializer(data = request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data

        restaurant = self.get_restaurant(request.user)
        restaurant = self.get_restaurant(request.user)
        if not restaurant:
            return Response({"error": "Restaurant not found for the user."}, status=status.HTTP_404_NOT_FOUND)
        restaurant_name = restaurant.resturent_name
        twilio_number = data["twilio_number"]
        twilio_account_sid = data["twilio_account_sid"]
        twilio_auth_token = data["twilio_auth_token"]

        if restaurant.twilio_number != twilio_number :
            restaurant.twilio_number = twilio_number



    

    def get_restaurant(self , user):
        try:
            restaurant = Restaurant.objects.get(owner = user)
            return restaurant
        except Restaurant.DoesNotExist:
            return None   

    # def create_phone_number(self, twilio_number, twilio_account_sid, twilio_auth_token, restaurant_name,assistant_id):
    #     """ Create the phone number using VAPI """
    #     response = requests.post(
    #         CREATE_PHONE,
    #         headers={"Authorization": VAPI_API},
    #         json={
    #             "provider": "twilio",
    #             "number": twilio_number,
    #             "name": restaurant_name,
    #             "twilioAccountSid": twilio_account_sid,
    #             "twilioAuthToken": twilio_auth_token,
    #             "assistantId": assistant_id
    #         },
    #     )
    #     phone_number = response.json() 
    #     return phone_number 
    
    # def create_assistant(self, restaurant_name,tool1_id, tool2_id):
    #     system_prompt = f"""[Identity]  
    #             You are the Restaurant Ordering Assistant, operating in a secure and friendly mode to take customer food orders and table reservations efficiently and clearly.

    #             [Context]  
    #             You are interacting with a customer who wants to make a table reservation. Focus on confirming a reservation. Only answer questions related to the reservation process or operating hours. Do not create information outside of this scope.

    #             [Style]  
    #             - Be polite, friendly, and professional.  
    #             - Speak clearly and at a natural pace.  
    #             - Keep the conversation focused on table booking only.  

    #             [Response Guidelines]  
    #             - Never say the words 'function', 'tool', or mention any internal processes.  
    #             - Do not end the call abruptly or say “transferring.”  
    #             - Stay in character as the restaurant assistant at all times.  
    #             - Maintain a helpful tone and keep the customer engaged until the task is complete.

    #             ---

    #             ### Reservation Flow

    #             Ask the user and gather the following fields:

    #             - customer_name: Ask **"Can I have your full name please?"**
    #             - guest_no: Ask **"How many guests will be attending?"**
    #             - cell_number: Ask **"May I have your phone number to send the confirmation?"**
    #             - reservation_time: 
    #             - Ask: **"Please Tell me the date just tell me date and month"**
    #                 - Add current year (2025) automatically
    #                 - Arrange them to YYYY-MM-DD for ISO format
    #             - Then ask: **"What time? For example, 7:30 PM"**
    #             - Combine the responses and convert them to ISO 8601 format like "YYYY-MM-DDTHH:MM:SSZ"

    #             ---

    #             🔹 Step 2: Trigger {restaurant_name}_restaurant_info Tool

    #             Once reservation_time is captured, call the {restaurant_name}_restaurant_info tool with

    #             From the response:
    #             extract: id and table_name

    #             Then, check restaurant.reservations from the same response.
    #             Each reservation entry includes at least:

    #             - For each restaurant.reservations item:
    #             - Compare its table_name with the current active device
    #             - If the table_name is not present, that table is free — assign it immediately.
    #             - If it is present, compare reservation_time:
    #                 - Add a 1-hour buffer to each existing reservation time
    #                 - If the new desired reservation_time does not conflict (i.e., does not fall within the 1-hour window), then assign that table.

    #             "device": {{
    #             "id": ..., 
    #             "table_name": ...
    #             }}

    #             you assign the first free table you will see no need to ask to customer
    #             And give a nice confirmation message. just give the information below:

    #             Thank you! I’ve confirmed your reservation.

    #             Here are the details:
    #             - Name: {{customer_name}}
    #             - Phone: {{cell_number}}
    #             - Date: {{reservation_date}}  
    #             - Time: {{reservation_time_formatted}}  
    #             - Table: {{device}}  

    #             We look forward to serving you at the restaurant. A confirmation has been sent to your phone.
    #             If the customer confirms, trigger the {restaurant_name}_reserveTable tool with the following values:
    #             """

    #     # API request to create assistant
    #     response = requests.post(
    #         CREATE_ASSISTANT,
    #         headers={"Authorization": VAPI_API},
    #         json={
    #             "name": restaurant_name,
    #             "firstMessage": "Hello! Welcome to our restaurant assistant. Would you like to book a table for reservation?",
    #             "model": {
    #                 "provider": "openai",
    #                 "model": "chatgpt-4o-latest",
    #                 "temperature": 0.4,
    #                 "maxTokens": 250,
    #                 "messages": [{"content": system_prompt, "role": "system"}],
    #                 "toolIds": [tool1_id, tool2_id],
    #             },
    #             "voice": {"provider": "vapi", "voiceId": "Elliot"},
    #             "firstMessageInterruptionsEnabled": False,
    #             "firstMessageMode": "assistant-speaks-first",
    #         },
    #     )
    #     assistant_data = response.json() 
    #     print(assistant_data)   
    #     return assistant_data  
    
    # def create_tools(self, restaurant_name, twilio_number):
    #     """Create tools for restaurant info and reservation management."""
    #     sanitized_name = sanitize_name(restaurant_name)
    #     # Create the first tool to get full data (restaurant info)
    #     tool1_response = requests.post(
    #         CREATE_TOOL,
    #         headers={"Authorization": VAPI_API},
    #         json={
    #             "type": "apiRequest",
    #             "method": "GET",
    #             "url": f"https://sacred-renewing-dove.ngrok-free.app/vapi/restaurants/full-data/{twilio_number}",
    #             "name": f"{sanitized_name}_restaurant_info"
    #         },
    #     )
        
    #     tool1_id = tool1_response.json().get("id")

    #     if not tool1_id:
    #         print("Tool 1 creation did not return an ID.")
    #         return None, None

    #     # Create the second tool to handle reservations
    #     tool2_response = requests.post(
    #         CREATE_TOOL,
    #         headers={"Authorization": VAPI_API},
    #         json={
    #             "type": "apiRequest",
    #             "method": "POST",
    #             "url": "https://sacred-renewing-dove.ngrok-free.app/vapi/reservations/create/",
    #             "name": f"{sanitized_name}_reserveTable",
    #             "body": {
    #                 "type": "object",
    #                 "required": ["customer_name", "guest_no", "cell_number", "reservation_time", "device"],
    #                 "properties": {
    #                     "device": {"description": "", "type": "number", "value": ""},
    #                     "guest_no": {"description": "", "type": "number", "value": ""},
    #                     "cell_number": {"description": "", "type": "string", "value": ""},
    #                     "customer_name": {"description": "", "type": "string", "value": ""},
    #                     "reservation_time": {"description": "", "type": "string", "value": ""}
    #                 }
    #             }
    #         },
    #     )
    #     tool2_id = tool2_response.json().get("id")

    #     if not tool2_id:
    #         print("Tool 2 creation did not return an ID.")
    #         return None, None

    #     return tool1_id, tool2_id
    

    # def create_assistance_record(self, restaurant, twilio_number, twilio_account_sid, twilio_auth_token, vapi_phone_number_id, assistant_id,tool1_id,tool2_id):
    #     """Create an Assistance record in the database."""
    #     assistance = Assistance(
    #         restaurant=restaurant,
    #         twilio_number=twilio_number,
    #         twilio_account_sid=twilio_account_sid,
    #         twilio_auth_token=twilio_auth_token,
    #         vapi_phone_number_id=vapi_phone_number_id,
    #         assistant_id=assistant_id,
    #         tool1_id=tool1_id,
    #         tool2_id=tool2_id
    #     )
    #     assistance.save()



     
