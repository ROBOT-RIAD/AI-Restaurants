from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserRestaurantSerializer, UserSerializer,RestaurantSerializer,CustomTokenObtainPairSerializer,SendOTPSerializer,VerifyOTPSerializer,ResetPasswordSerializer,RestaurantFullDataserializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.parsers import MultiPartParser, FormParser
from django.views.decorators.csrf import csrf_exempt
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from accounts.models import User,PasswordResetOTP
from rest_framework.exceptions import ValidationError
from .translations import translate_text
from rest_framework_simplejwt.views import TokenObtainPairView,TokenRefreshView
from django.core.mail import send_mail
from django.conf import settings
from table.models import Table, Reservation
from restaurants.models import Restaurant,OpenAndCloseTime
from items.models import Item
from django.utils.timezone import now
from order.models import Order
from customerService.models import CustomerService
from AIvapi.models import Assistance,CallInformations
from django.db.models import F, Sum, Func, IntegerField
from subscription.models import Subscription
from delivery_management.models import AreaManagement




class RegisterApiView(CreateAPIView):
    """
    API endpoint for registering a new user and creating a restaurant.
    Also provides JWT token upon successful registration.
    """
    queryset = User.objects.all()
    serializer_class = UserRestaurantSerializer
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        tags=["Authentication"],
        operation_description="Register a new user and create a restaurant. Provides JWT tokens.",
        request_body=UserRestaurantSerializer,
        responses={
            201: openapi.Response(
                description="User and restaurant created successfully",
                examples={
                    'application/json': {
                        'access_token': 'your_jwt_access_token_here',
                        'refresh_token': 'your_jwt_refresh_token_here',
                        'user': {
                            'id': 1,
                            'email': 'user@example.com',
                            'role': 'Owner',
                        },
                        'restaurant': {
                            'resturent_name': 'Best Restaurant',
                            'address': '123 Street, City',
                            'phone_number_1': '1234567890',
                            'twilio_number': '9876543210',
                            'opening_time': '10:00:00',
                            'closing_time': '22:00:00',
                            'website': 'https://example.com',
                            'iban': 'IBAN1234567890',
                            'tax_number': 'TAX123456',
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="Bad Request, validation errors",
                examples={
                    'application/json': {
                        "email": ["This field is required."]
                    }
                }
            ),
            500: openapi.Response(
                description="Internal Server Error",
                examples={
                    'application/json': {
                        "error": "Error message"
                    }
                }
            )
        },
        manual_parameters=[
            openapi.Parameter(
                'lean', 
                openapi.IN_QUERY, 
                description="Language code for translation (default is 'en').", 
                type=openapi.TYPE_STRING,
                default='EN'
            ),
        ],
    )
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        try:
            lean = request.query_params.get('lean')
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user, restaurant = serializer.save()



            if lean != 'EN':
                restaurant.resturent_name = translate_text(restaurant.resturent_name, 'EN')
                restaurant.address = translate_text(restaurant.address, 'EN')
                restaurant.save()


            table_names = ['Table 1A', 'Table 1B', 'Table 1C', 'Table 1D', 'Table 1E']

            for table_name in table_names:
                Table.objects.create(
                    restaurant=restaurant,
                    table_name=table_name,
                    total_set=4
                )

            default_open_time = time(hour=6, minute=0, second=0)
            default_close_time = time(hour=17, minute=0, second=0)

            days_of_week = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
            
            for day in days_of_week:
                OpenAndCloseTime.objects.create(
                    restaurant=restaurant,
                    day_of_week=day,
                    opening_time=default_open_time,
                    closing_time=default_close_time
                )

            # Generate JWT tokens (refresh and access)
            refresh = RefreshToken.for_user(user)
            refresh['email'] = user.email
            refresh['role'] = user.role
            access_token = str(refresh.access_token)

            data = RestaurantSerializer(restaurant,context ={'request' : request}).data

            if lean != 'EN':
                data['resturent_name'] = translate_text(restaurant.resturent_name, lean)
                data['address'] = translate_text(restaurant.address, lean)

            response_data = {
                'access_token': access_token,
                'refresh_token': str(refresh), 
                'user': {
                    'id' : user.id,
                    'email': user.email,
                    'role': user.role,
                },
                'restaurant':data,
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        except ValidationError as ve:
            return Response({"errors": ve.detail}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)\
            



class LoginAPIView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        tags=["Authentication"],
        manual_parameters=[
            openapi.Parameter(
                'lean', 
                openapi.IN_QUERY, 
                description="Language code for translation (default is 'en').", 
                type=openapi.TYPE_STRING,
                default='EN'
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        try:
            lean = request.query_params.get('lean')
            response = super().post(request, *args, **kwargs)
            response_data = response.data

            if lean != 'EN' and 'restaurant' in response_data:
                restaurant = response_data['restaurant']
                restaurant['resturent_name'] = translate_text(restaurant.get('resturent_name'), lean)
                restaurant['address'] = translate_text(restaurant.get('address'), lean)

            return Response(response_data, status=status.HTTP_200_OK)
        except ValidationError as ve:
            return Response({"error": ve.detail['non_field_errors'][0]}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e :
            return Response({"error": str(e)}, status= status.HTTP_500_INTERNAL_SERVER_ERROR)
        

    

class CustomTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(tags=["Authentication"])
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except Exception as e :
            return Response({"error":str(e)} , status= status.HTTP_500_INTERNAL_SERVER_ERROR)
        



class SendOTPView(APIView):
    permission_classes = [AllowAny]
 
    @swagger_auto_schema(
        request_body=SendOTPSerializer,
        tags=["Forgot Password"],
        operation_summary="Send OTP to email",
        responses={200: openapi.Response('OTP sent'), 400: 'Bad Request'}
    )
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            otp_record = PasswordResetOTP.objects.create(user=user)
        
            # Send OTP via email
            send_mail(
            subject='Your OTP Code',
            message=f'Your OTP is: {otp_record.otp}',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            )

            return Response({
                "message": "OTP sent to your email.",
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "Failed to send OTP."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=VerifyOTPSerializer,
        tags=["Forgot Password"],
        operation_summary="Verify OTP",
        responses={200: openapi.Response('OTP verified'), 400: 'Invalid OTP'}
    )

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            otp_record = PasswordResetOTP.objects.filter(
                user=user, otp=otp, is_verified=False
            ).latest('created_at')
        except PasswordResetOTP.DoesNotExist:
            return Response({"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)

        otp_record.is_verified = True
        otp_record.save()

        return Response({"message": "OTP verified successfully."}, status=status.HTTP_200_OK)




class ResetPasswordView(APIView):
    permission_classes = [AllowAny] 

    @swagger_auto_schema(
        request_body=ResetPasswordSerializer,
        manual_parameters=[
            openapi.Parameter(
                'email',
                openapi.IN_QUERY,
                description="Email address to reset password for",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        tags=["Forgot Password"],
        operation_summary="Reset password after OTP verification",
        responses={200: openapi.Response('Password reset successful'), 400: 'Bad Request'}
    )

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = request.query_params.get('email')
        if not email:
            return Response({"error": "Email is required in query params."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            otp_record = PasswordResetOTP.objects.filter(
                user=user, is_verified=True
            ).latest('created_at')
        except PasswordResetOTP.DoesNotExist:
            return Response({"error": "OTP not verified or expired."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            otp_record.delete()
            return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error" : e}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



def clean_twilio_number(twilio_number: str) -> str:
    """
    Removes unwanted whitespace/newline from a Twilio number.
    """
    if not twilio_number:
        return None
    return twilio_number.strip()



class RestaurantFullDataAPIView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RestaurantFullDataserializer

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "twilio_number": openapi.Schema(type=openapi.TYPE_STRING)
            },
            required=["twilio_number"],
        ),
        responses={200: "Restaurant full data (info, items, tables, reservations)"},
        tags=["Webhook"]
    )
    def post(self, request):
        twilio_number = request.data.get("twilio_number")
        twilio_number = clean_twilio_number(twilio_number)

        if not twilio_number:
            return Response({"error": "twilio_number is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            restaurant = Restaurant.objects.get(twilio_number=twilio_number)
        except Restaurant.DoesNotExist:
            return Response({"error": "Restaurant not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get related data
        items = Item.objects.filter(restaurant=restaurant)
        tables = Table.objects.filter(restaurant=restaurant)
        today = now().date()
        reservations = Reservation.objects.filter(table__restaurant=restaurant, date__gte=today)

        # Group reservations by table
        table_reservations = {}
        for reservation in reservations:
            table_reservations.setdefault(reservation.table.id, []).append({
                "id": reservation.id,
                "guest_no": reservation.guest_no,
                "status": reservation.status,
                "date": reservation.date,
                "from_time": reservation.from_time,
                "to_time": reservation.to_time,
                "table": reservation.table.table_name,
                "email": reservation.email,
            })
        # Collect distinct phone numbers
        phones = set(
            list(
                Reservation.objects.filter(table__restaurant=restaurant)
                .exclude(phone_number__isnull=True)
                .values_list("phone_number", flat=True)
            )
            + list(
                Order.objects.filter(restaurant=restaurant)
                .exclude(phone__isnull=True)
                .values_list("phone", flat=True)
            )
            + list(
                CustomerService.objects.filter(restaurant=restaurant)
                .exclude(phone_number__isnull=True)
                .values_list("phone_number", flat=True)
            )
        )

        customer_data = {}

        for phone in phones:
            # Latest Reservation
            last_res = (
                Reservation.objects.filter(table__restaurant=restaurant, phone_number=phone)
                .order_by("-created_at")
                .first()
            )
            res_count = Reservation.objects.filter(table__restaurant=restaurant, phone_number=phone).count()

            # Latest Order
            last_order = (
                Order.objects.filter(restaurant=restaurant, phone=phone)
                .order_by("-created_at")
                .first()
            )
            order_count = Order.objects.filter(restaurant=restaurant, phone=phone).count()

            # Latest Service
            last_service = (
                CustomerService.objects.filter(restaurant=restaurant, phone_number=phone)
                .order_by("-created_at")
                .first()
            )
            service_count = CustomerService.objects.filter(restaurant=restaurant, phone_number=phone).count()

             # List of non-None records
            records = [last_res, last_order, last_service]

            # Filter out None values before finding the latest record
            records = [record for record in records if record is not None]

            # Pick the most recent record
            latest_record = max(records, key=lambda x: x.created_at if x else None) if records else None

            if latest_record:
                if isinstance(latest_record, Reservation):
                    last_type = "reservation"
                    name = latest_record.customer_name
                elif isinstance(latest_record, Order):
                    last_type = "order"
                    name = latest_record.customer_name
                elif isinstance(latest_record, CustomerService):
                    last_type = "service"
                    name = latest_record.customer_name
                else:
                    last_type, name = None, None
            else:
                last_type, name = None, None

            customer_data[phone] = {
                "name": name,
                "phone": phone,
                "most_recent_last": {
                    "type": last_type,
                    "created_at": latest_record.created_at if latest_record else None,
                },
                "total_create": res_count + order_count + service_count,
            }


        # Ensure the duration is a valid integer by rounding or converting it
        # Use correct SQL syntax for CAST and ensure duration is handled as a float before casting to integer
        total_call_duration = CallInformations.objects.filter(
            assistant_id__in=Assistance.objects.filter(restaurant=restaurant).values_list('assistant_id', flat=True)
        ).aggregate(
            total_duration=Sum(Func(F('duration_seconds'), function='CAST', template='CAST(CAST(%(expressions)s AS FLOAT) AS INTEGER)', output_field=IntegerField()))
        )



        total_duration_seconds = total_call_duration['total_duration'] if total_call_duration['total_duration'] else 0

        total_used_minutes = total_duration_seconds / 60

        try:
            subscription = Subscription.objects.filter(user=restaurant.owner, is_active=True).first()
        except Subscription.DoesNotExist:
            subscription = None

        areas = AreaManagement.objects.filter(restaurant=restaurant)

        open_close_times_qs = OpenAndCloseTime.objects.filter(restaurant=restaurant)
        open_close_times = [
            {
                "day_of_week": oc.day_of_week,
                "opening_time": oc.opening_time,
                "closing_time": oc.closing_time,
            }
            for oc in open_close_times_qs
        ] if open_close_times_qs.exists() else []

        # Prepare response
        data = {
            "restaurant": {
                "id": restaurant.id,
                "name": restaurant.resturent_name,
                "address": restaurant.address,
                "phone_number_1": restaurant.phone_number_1,
                "twilio_number": restaurant.twilio_number,
                "opening_time": restaurant.opening_time,
                "closing_time": restaurant.closing_time,
                "website": restaurant.website,
                "iban": restaurant.iban,
                "tax_number": restaurant.tax_number,
                "total_vapi_minutes" : restaurant.total_vapi_minutes,
                "total_used_minutes_vapi": total_used_minutes,
            },
            "subscription": {
                "package_name": subscription.package_name if subscription else None,
                "status": subscription.status if subscription else None,
                "start_date": subscription.start_date if subscription else None,
                "end_date": subscription.end_date if subscription else None,
                "cancel_at_period_end": subscription.cancel_at_period_end if subscription else None,
                "is_active": subscription.is_active if subscription else None,
            } if subscription else {},
            "items": [
                {
                    "id": item.id,
                    "name": item.item_name,
                    "status": item.status,
                    "description": item.descriptions,
                    "image": item.image.url if item.image else None,
                    "category": item.category,
                    "price": str(item.price),
                    "discount": str(item.discount) if item.discount else None,
                    "preparation_time": item.preparation_time,
                }
                for item in items
            ],
            "tables": [
                {
                    "id": table.id,
                    "name": table.table_name,
                    "status": table.status,
                    "reservation_status": table.reservation_status,
                    "total_set": table.total_set,
                    "reservations": table_reservations.get(table.id, []),  # Add reservations grouped by table
                }
                for table in tables
            ],
            "customers": list(customer_data.values()),
            "areas": [
                {
                    "id": area.id,
                    "postalcode": area.postalcode,
                    "estimated_delivery_time": area.estimated_delivery_time,
                    "delivery_fee": str(area.delivery_fee),
                }
                for area in areas
            ],
            "open_close_times": open_close_times
        }

        return Response(data, status=status.HTTP_200_OK)
    



