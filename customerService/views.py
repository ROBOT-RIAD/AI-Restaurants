from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from .serializers import CustomerServiceSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from restaurants.models import Restaurant
from table.models import Reservation
from order.models import Order
from .models import CustomerService
from rest_framework.permissions import IsAuthenticated

# Create your views here.
class CreateCustomerService(APIView):
    permission_classes = [AllowAny] 

    @swagger_auto_schema(
        operation_description="Create a new Customer Service record.",
        request_body=CustomerServiceSerializer,
        responses={
            201: openapi.Response('Customer service created successfully', CustomerServiceSerializer),
            400: 'Bad Request. Validation errors occurred.',
        },
        tags=['Webhook']
    )
    def post(self, request, *args, **kwargs):
        data = request.data
        restaurant_id = data.get('restaurant')
        if restaurant_id:
            try:
                restaurant = Restaurant.objects.get(id= restaurant_id)
            except Restaurant.DoesNotExist:
                return Response({'error' : "Restaurant not found"},status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({'error': 'Restaurant ID is required'}, status=status.HTTP_400_BAD_REQUEST)   
        serializer = CustomerServiceSerializer(data=data)
        if serializer.is_valid():
            serializer.save(restaurant=restaurant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class CustomerSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get customer summary for reservations, orders, and services. "
                              "Search by phone using ?phone=NUMBER",
        manual_parameters=[
            openapi.Parameter(
                "phone",
                openapi.IN_QUERY,
                description="Search by phone number (partial or full match)",
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Customer summary list",
                examples={
                    "application/json": [
                        {
                            "name": "John Doe",
                            "phone": "1234567890",
                            "most_recent_last": {
                                "type": "order",
                                "created_at": "2025-09-08T14:30:00Z"
                            },
                            "total_create": 5
                        }
                    ]
                },
            ),
            404: "Restaurant not found for this user",
        },
        tags=['customer Api'],
    )

    def get(self, request, *args, **kwargs):
        user = request.user
        
        try:
            restaurant = user.restaurants.first()
        except Exception:
            restaurant = Restaurant.objects.filter(owner=user).first()

        if not restaurant:
            return Response({"detail": "Restaurant not found for this user"}, status=404)

        phone_filter = request.query_params.get("phone")

        customer_data = {}

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

        # 🔹 If searching, reduce phones to just that one
        if phone_filter:
            phones = {phone for phone in phones if phone_filter in phone}

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

            # Pick the most recent record
            latest_record = max(
                [last_res, last_order, last_service],
                key=lambda x: x.created_at if x else None,
            )

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

        return Response(list(customer_data.values()))



