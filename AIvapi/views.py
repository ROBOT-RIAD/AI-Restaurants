from django.conf import settings
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import AssistanceCreateSerializer,CallInformationsSerializer,CallInformationsCallbackUpdateSerializer,UpdateVoiceIdSerializer, UpdateTwilioCredsSerializer,AssistanceSerializer
from restaurants.models import Restaurant
from .models import Assistance,CallInformations
import requests
from rest_framework import status
import re
from .CallHook import vapi_webhook
from .models import Assistance
from .agent import AGENT
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.permissions import AllowAny
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError
from datetime import datetime
from .update_agent import UpdateAgent
from restaurants.models import Restaurant,OpenAndCloseTime
import pytz
from accounts.permissions import IsAdminOrOwner,IsAdminRole
from customer.models import Customer
from .delete_agent import delete_agent

VAPI_API = settings.VAPI_API


# Create your views here.

def sanitize_name(restaurant_name):
    sanitized_name = re.sub(r'[^a-zA-Z0-9_-]', '_', restaurant_name)
    return sanitized_name




class AssistantCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create AI Assistant for a restaurant",
        operation_description="Creates an AI-powered assistant and links a Twilio number for the restaurant.",
        request_body=AssistanceCreateSerializer,
        manual_parameters=[
            openapi.Parameter(
                "restaurant_id",
                openapi.IN_QUERY,
                description="ID of the restaurant for which to create assistant",
                type=openapi.TYPE_INTEGER,
                required=True,
            ),
        ],
        responses={
            201: openapi.Response(
                description="Assistant created successfully",
                examples={
                    "application/json": {
                        "assistant_id": "06e1cb58-2247-45c6-bfab-c6e92f665bbb",
                        "vapi_phone_number_id": "df84aab1-3d76-4fd0-89a5-2dd83e14a812",
                        "twilio_number": "+4915888648996",
                        "restaurant": "Cafe Rio",
                    }
                },
            ),
            400: "Bad Request – Invalid data or assistant already exists",
            404: "Restaurant not found",
            500: "Server error – Failed to create assistant or phone number",
        },
        tags=['VAPI']
    )

    def post(self , request):
        restaurant_id = request.query_params.get("restaurant_id")
        serializer = AssistanceCreateSerializer(data = request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data

        try:
            restaurant = Restaurant.objects.get(id=restaurant_id)
        except Restaurant.DoesNotExist:
            return Response(
                {"error": "Restaurant not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not restaurant:
            return Response({"error": "Restaurant not found for the user."}, status=status.HTTP_404_NOT_FOUND)
        twilio_number = data["twilio_number"]
        twilio_account_sid = data["twilio_account_sid"]
        twilio_auth_token = data["twilio_auth_token"]


        phone_number_1 = restaurant.phone_number_1
        if not re.match(r'^\+\d{1,4}\d{6,14}$', phone_number_1):
            return Response(
                {"You must add a country code to the phone number. It should start with a '+' followed by the country code."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if hasattr(restaurant, "ai_assistance"):
            return Response(
                {"error": "Assistant already exists for this restaurant."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if restaurant.twilio_number != twilio_number :
            restaurant.twilio_number = twilio_number

        agent = AGENT()

        try:
            assistant_response, phone_response = agent.create_agent(
                voice=data.get("voice", "matilda"),
                restaurant_name=restaurant.resturent_name,
                speed=data.get("speed", 1.0),
                twillo_num=twilio_number,
                ssid=twilio_account_sid,
                restaurant_fallback=restaurant.phone_number_1,
                auth_token=twilio_auth_token,
                webhook='https://api.trusttaste.ai/vapi-webhook/',
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        assistance = Assistance.objects.create(
            restaurant=restaurant,
            twilio_number=twilio_number,
            twilio_account_sid=twilio_account_sid,
            twilio_auth_token=twilio_auth_token,
            vapi_phone_number_id=phone_response.get("id"),
            assistant_id=assistant_response.get("id"),
        )
        restaurant.twilio_number = twilio_number
        restaurant.save()
        serializer = AssistanceCreateSerializer(assistance)


        return Response(serializer.data, status=status.HTTP_201_CREATED)




class UpdateVoiceIdAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Update the voiceId for the authenticated user's restaurant",
        request_body=UpdateVoiceIdSerializer,
        responses={
            200: openapi.Response('Success'),
            400: 'Bad Request',
            404: 'Assistance or Restaurant Not Found',
        },
        tags=['VAPI']
    )

    def post(self, request):
        
        try:
            restaurant = request.user.restaurants.first()
            if not restaurant:
                return Response({"detail": "No restaurant associated with user."}, status=status.HTTP_404_NOT_FOUND)
            
            assistance = restaurant.ai_assistance
        except Assistance.DoesNotExist:
            return Response({"detail": "Assistance not found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = UpdateVoiceIdSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        speed = serializer.validated_data.get('speed')
        voice_id = serializer.validated_data.get('voice_id', 'matilda')

        agent = UpdateAgent(agent_id=assistance.assistant_id, phone_id=assistance.vapi_phone_number_id)
        try:
            response = agent.update_voiceId(speed=speed, voice_id=voice_id)
            assistance.speed = speed
            assistance.voice = voice_id
            assistance.save(update_fields=['speed', 'voice'])
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)




class UpdateTwilioCredsAPIView(APIView):
    permission_classes = [IsAuthenticated,IsAdminOrOwner]

    @swagger_auto_schema(
        operation_description="Update Twilio credentials for the authenticated user's restaurant",
        request_body=UpdateTwilioCredsSerializer,
        responses={
            200: openapi.Response('Success'),
            400: 'Bad Request',
            404: 'Assistance or Restaurant Not Found',
        },
        manual_parameters=[
            openapi.Parameter(
                'restaurant_id',
                openapi.IN_QUERY,
                description="(Admin only) ID of the restaurant to update",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        tags=['VAPI']
    )

    def patch(self, request):
        restaurant_id = request.query_params.get("restaurant_id")

        if request.user.role == "admin" and restaurant_id:
            restaurant = Restaurant.objects.filter(id=restaurant_id).first()
            if not restaurant:
                return Response(
                    {"detail": "Restaurant not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            restaurant = request.user.restaurants.first()
            if not restaurant:
                return Response(
                    {"detail": "No restaurant associated with this user."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
        try:
            assistance = restaurant.ai_assistance
        except Assistance.DoesNotExist:
            return Response(
                {"detail": "Assistance not found for this restaurant."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = UpdateTwilioCredsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        twilio_number = serializer.validated_data['twilio_number']
        account_sid = serializer.validated_data['twilio_account_sid']
        auth_token = serializer.validated_data['twilio_auth_token']

        agent = UpdateAgent(agent_id=assistance.assistant_id, phone_id=assistance.vapi_phone_number_id)
        try:
            response = agent.update_twilio_creds(
                updated_twilio_number=twilio_number,
                updated_sid=account_sid,
                updated_auth_token=auth_token,
            )
            assistance.twilio_number = twilio_number
            assistance.twilio_account_sid = account_sid
            assistance.twilio_auth_token = auth_token
            assistance.save()
            restaurant.twilio_number = twilio_number
            restaurant.save()
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)





class VapiWebhookAsyncAPIView(APIView):
    permission_classes = [AllowAny]
    """
    Async DRF view for handling VAPI webhooks.
    """
    request_body_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'message': openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='VAPI call message payload',
            )
        },
        required=['message']
    )

    @swagger_auto_schema(
        request_body=request_body_schema,
        responses={
            200: openapi.Response(
                description="Webhook ignored",
                examples={"application/json": {"status": "ignored", "reason": "not end-of-call-report"}}
            ),
            201: openapi.Response(
                description="Call information stored",
                schema=CallInformationsSerializer
            ),
            400: "Error parsing webhook"
        }
        ,
        tags=['VAPI']
    )
    def post(self, request, *args, **kwargs):
        try:
            parsed = vapi_webhook(request)

            if parsed.get("status") == "ignored":
                return Response(parsed, status=status.HTTP_200_OK)
            

            assistant_id = parsed.get("assistant_id")
            assistance = Assistance.objects.get(assistant_id=assistant_id)
            restaurant = assistance.restaurant

            call_date_utc = parsed.get("call_date")  # Should be in ISO format or datetime
            call_datetime = datetime.fromisoformat(call_date_utc) if isinstance(call_date_utc, str) else call_date_utc

            local_tz = pytz.timezone('Europe/Berlin')
            call_datetime_local = call_datetime.astimezone(local_tz)
            call_time = call_datetime_local.time()

            callback_value = True  

            if parsed.get("type") == "order":
                local_tz = pytz.timezone('Europe/Berlin')
                call_datetime_local = call_datetime.astimezone(local_tz)
                call_time = call_datetime_local.time()
                day_of_week = call_datetime_local.strftime('%A').lower()

                callback_value = True 
                try:
                    day_schedule = OpenAndCloseTime.objects.get(restaurant=restaurant, day_of_week=day_of_week)
                except OpenAndCloseTime.DoesNotExist:
                    day_schedule = None

                if day_schedule:
                    if day_schedule.is_closed:
                        callback_value = False
                    elif day_schedule.opening_time and day_schedule.closing_time:
                        if not (day_schedule.opening_time <= call_time <= day_schedule.closing_time):
                            callback_value = False


            phone_number = parsed.get("phone")
            customer_name = None
            if phone_number:
                customer = Customer.objects.filter(phone=phone_number).first()
                if customer:
                    customer_name = customer.customer_name

            # Save to DB
            call_info = CallInformations.objects.create(
                type=parsed.get("type"),
                call_date_utc=parsed.get("call_date"),
                phone = parsed.get("phone"),
                duration_seconds=str(parsed.get("duration_seconds") or 0),
                summary=parsed.get("summary") or "",
                recording=parsed.get("recording") or "",
                callback=callback_value,
                assistant_id=parsed.get("assistant_id") or "",
                cost=parsed.get("cost") or 0,
                customer_name=customer_name
            )

            serializer = CallInformationsSerializer(call_info)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)




class UserCallInformationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    success_response = openapi.Response(
        description="List of call information",
        schema=CallInformationsSerializer(many=True)
    )

    error_response_404 = openapi.Response(
        description="Restaurant or Assistant not found",
        examples={
            "application/json": {
                "error": "No restaurant linked to your account."
            }
        }
    )

    date_param = openapi.Parameter(
        'date', openapi.IN_QUERY, description="Filter calls by a specific date (YYYY-MM-DD)",
        type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE,required=False
    )


    callback_param = openapi.Parameter(
        'callback', openapi.IN_QUERY, description="Filter calls by callback status (true/false)",
        type=openapi.TYPE_BOOLEAN, required=False
    )


    type_param = openapi.Parameter(
        'type', openapi.IN_QUERY, description="Filter calls by type (e.g., 'service', 'reservation', 'order')",
        type=openapi.TYPE_STRING, required=False
    )

    @swagger_auto_schema(
        operation_description="Retrieve all call information associated with the logged-in user's restaurant assistant",
        responses={
            status.HTTP_200_OK: success_response,
            status.HTTP_404_NOT_FOUND: error_response_404
        },
        tags=["CALL"],
        manual_parameters=[date_param, callback_param, type_param]
    )  

    def get(self, request):
        date_str = request.query_params.get('date', None)
        callback_str = request.query_params.get('callback', None)
        type_str = request.query_params.get('type', None)

        try:
            if date_str:
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
            else:
                date = None

            # Handle callback filter (True/False)
            if callback_str is not None:
                callback = callback_str.lower() in ['true', '1', 't', 'y', 'yes']
            else:
                callback = None

            # Handle type filter
            if type_str:
                call_type = type_str
            else:
                call_type = None

            restaurant = request.user.restaurants.get()
            assistance = restaurant.ai_assistance
            assistant_id = assistance.assistant_id
            calls = CallInformations.objects.filter(assistant_id=assistant_id)
            if date:
                calls = calls.filter(call_date_utc__date=date)
            if callback is not None:
                calls = calls.filter(callback=callback)
            if call_type:
                calls = calls.filter(type=call_type)
            serializer = CallInformationsSerializer(calls, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Restaurant.DoesNotExist:
            return Response({"error": "No restaurant linked to your account."}, status=status.HTTP_404_NOT_FOUND)

        except Assistance.DoesNotExist:
            return Response({"error": "No AI assistance set for your restaurant."}, status=status.HTTP_404_NOT_FOUND)




class UserSingleCallInformationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    success_response = openapi.Response(
        description="Single call information",
        schema=CallInformationsSerializer()
    )

    error_response_404 = openapi.Response(
        description="Not found",
        examples={
            "application/json": {
                "error": "Call information not found."
            }
        }
    )

    @swagger_auto_schema(
        operation_description="Retrieve a single call information by ID associated with the logged-in user's restaurant assistant",
        responses={
            status.HTTP_200_OK: success_response,
            status.HTTP_404_NOT_FOUND: error_response_404,
        },
        tags=["CALL"],
        manual_parameters=[
            openapi.Parameter(
                'call_id',
                openapi.IN_PATH,
                description="ID of the call information",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ]
    )
    def get(self, request, call_id):
        try:
            restaurant = request.user.restaurants.get()
            assistance = restaurant.ai_assistance
            assistant_id = assistance.assistant_id
            call_info = CallInformations.objects.get(id=call_id, assistant_id=assistant_id)

            serializer = CallInformationsSerializer(call_info)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Restaurant.DoesNotExist:
            return Response({"error": "No restaurant linked to your account."}, status=status.HTTP_404_NOT_FOUND)

        except Assistance.DoesNotExist:
            return Response({"error": "No AI assistance set for your restaurant."}, status=status.HTTP_404_NOT_FOUND)

        except CallInformations.DoesNotExist:
            return Response({"error": "Call information not found."}, status=status.HTTP_404_NOT_FOUND)





class UpdateCallCallbackAPIView(APIView):
    permission_classes = [IsAuthenticated]


    request_body = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['callback'],
        properties={
            'callback': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Callback status to update')
        },
    )

    success_response = openapi.Response(
        description="Callback field updated successfully",
        schema=CallInformationsSerializer()
    )

    error_response_404 = openapi.Response(
        description="Not found",
        examples={
            "application/json": {
                "error": "Call information not found."
            }
        }
    )

    @swagger_auto_schema(
        operation_description="Update the callback field of a call information by ID linked to the logged-in user's restaurant assistant",
        request_body=request_body,
        responses={
            status.HTTP_200_OK: success_response,
            status.HTTP_400_BAD_REQUEST: "Invalid input data",
            status.HTTP_404_NOT_FOUND: error_response_404
        },
        tags=["CALL"],
        manual_parameters=[
            openapi.Parameter(
                'call_id',
                openapi.IN_PATH,
                description="ID of the call information to update",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ]
    )

    def patch(self, request, call_id):
        try:

            restaurant = request.user.restaurants.get()
            assistance = restaurant.ai_assistance
            assistant_id = assistance.assistant_id

            call_info = CallInformations.objects.get(id=call_id, assistant_id=assistant_id)

            serializer = CallInformationsCallbackUpdateSerializer(call_info, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.validated_data['callback_track'] = True
                serializer.save()
                full_serializer = CallInformationsSerializer(call_info)
                return Response(full_serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Restaurant.DoesNotExist:
            return Response({"error": "No restaurant linked to your account."}, status=status.HTTP_404_NOT_FOUND)

        except Assistance.DoesNotExist:
            return Response({"error": "No AI assistance set for your restaurant."}, status=status.HTTP_404_NOT_FOUND)

        except CallInformations.DoesNotExist:
            return Response({"error": "Call information not found."}, status=status.HTTP_404_NOT_FOUND)




class GetRestaurantAssistantAPIView(APIView):
    """
    Retrieve AI Assistant information for the restaurant owned by the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get AI Assistant Info for Restaurant",
        operation_description="""
        Retrieves the AI Assistant details (voice, speed, Twilio info, etc.)
        for the restaurant owned by the currently authenticated user.
        """,
        responses={
            200: AssistanceSerializer,
            404: openapi.Response(
                description="Restaurant or AI Assistant not found.",
                examples={
                    "application/json": {"error": "No AI Assistant found for your restaurant."}
                },
            ),
        },
        tags=['VAPI']
    )
    def get(self, request):
        user = request.user

        try:
            restaurant = Restaurant.objects.get(owner=user)
        except Restaurant.DoesNotExist:
            return Response(
                {"error": "You do not own any restaurant."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            assistant = Assistance.objects.get(restaurant=restaurant)
        except Assistance.DoesNotExist:
            return Response(
                {"error": "No AI Assistant found for your restaurant."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AssistanceSerializer(assistant)
        return Response(serializer.data, status=status.HTTP_200_OK)





class DeleteRestaurantsAssistantAPIView(APIView):
    permission_classes = [IsAdminRole]

    @swagger_auto_schema(
        operation_description="Delete an AI Assistant by restaurant ID.",
        manual_parameters=[
            openapi.Parameter(
                'restaurant_id',
                openapi.IN_PATH,
                description="Restaurant ID",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        tags=["VAPI"]
    )
    def delete(self, request, restaurant_id):
        try:
            restaurant = Restaurant.objects.get(id=restaurant_id)
        except Restaurant.DoesNotExist:
            return Response(
                {"error": "Restaurant not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 2. Assistance Check
        try:
            assistance = restaurant.ai_assistance
        except Assistance.DoesNotExist:
            return Response(
                {"error": "AI Assistant does not exist for this restaurant."},
                status=status.HTTP_404_NOT_FOUND
            )
        try:
            delete_agent(
                assistance.assistant_id,
                assistance.vapi_phone_number_id
            )
        except Exception as e:
            return Response(
                {"error": f"VAPI delete failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        assistance.delete()
        restaurant.twilio_number = None
        restaurant.save()

        return Response(
            {"message": "AI Assistant & phone number deleted successfully."},
            status=status.HTTP_200_OK
        )

        



