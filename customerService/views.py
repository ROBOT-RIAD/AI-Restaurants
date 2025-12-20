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
from rest_framework import generics
from datetime import datetime,timedelta
import pytz
from django.utils.dateparse import parse_date
from datetime import datetime, timedelta
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

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
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"restaurant_{restaurant.id}",
                {
                    "type": "customer_service_created",
                    "service": serializer.data
                }
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class CustomerSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get customer summary for reservations, orders, and services. "
                              "Search by phone using ?phone=NUMBER. Filter by created after date using ?created_at=YYYY-MM-DD.",
        manual_parameters=[
            openapi.Parameter("phone", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("created_at", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
        ],
        tags=['customer Api'],
    )
    def get(self, request):
        user = request.user

        try:
            restaurant = user.restaurants.first()
        except Exception:
            restaurant = Restaurant.objects.filter(owner=user).first()

        if not restaurant:
            return Response({"detail": "Restaurant not found for this user"}, status=404)

        phone_filter = request.query_params.get("phone")
        created_at_filter = request.query_params.get("created_at")

        # Date filter handling
        created_at_date = None
        if created_at_filter:
            created_at_date = parse_date(created_at_filter)
            if not created_at_date:
                return Response({"detail": "Invalid date format. Use YYYY-MM-DD."}, status=400)

            start_of_day = datetime.combine(created_at_date, datetime.min.time(), tzinfo=pytz.UTC)
            end_of_day = start_of_day + timedelta(days=1)

        # STEP 1: Collect all phones from related models
        phones = set()

        # Reservations → Customer.phone
        res_customers = Reservation.objects.filter(
            table__restaurant=restaurant,
            customer__isnull=False
        ).values_list("customer__phone", flat=True)

        phones.update([p for p in res_customers if p])

        # Orders → Customer.phone
        order_customers = Order.objects.filter(
            restaurant=restaurant,
            customer__isnull=False
        ).values_list("customer__phone", flat=True)

        phones.update([p for p in order_customers if p])

        # CustomerService → Customer.phone
        service_customers = CustomerService.objects.filter(
            restaurant=restaurant,
            customer__isnull=False
        ).values_list("customer__phone", flat=True)

        phones.update([p for p in service_customers if p])

        # Apply ?phone= filter
        if phone_filter:
            phones = {phone for phone in phones if phone_filter in phone}

        # STEP 2: Build summary for each phone
        customer_data = {}

        for phone in phones:
            # Latest Reservation
            last_res = Reservation.objects.filter(
                table__restaurant=restaurant,
                customer__phone=phone
            )
            if created_at_date:
                last_res = last_res.filter(created_at__range=(start_of_day, end_of_day))
            last_res = last_res.order_by("-created_at").first()
            res_count = Reservation.objects.filter(
                table__restaurant=restaurant,
                customer__phone=phone
            ).count()

            # Latest Order
            last_order = Order.objects.filter(
                restaurant=restaurant,
                customer__phone=phone
            )
            if created_at_date:
                last_order = last_order.filter(created_at__range=(start_of_day, end_of_day))
            last_order = last_order.order_by("-created_at").first()
            order_count = Order.objects.filter(
                restaurant=restaurant,
                customer__phone=phone
            ).count()

            # Latest CustomerService
            last_service = CustomerService.objects.filter(
                restaurant=restaurant,
                customer__phone=phone
            )
            if created_at_date:
                last_service = last_service.filter(created_at__range=(start_of_day, end_of_day))
            last_service = last_service.order_by("-created_at").first()
            service_count = CustomerService.objects.filter(
                restaurant=restaurant,
                customer__phone=phone
            ).count()

            # Find latest record
            latest_record = max(
                [last_res, last_order, last_service],
                key=lambda obj: obj.created_at.astimezone(pytz.UTC) if obj else datetime(1, 1, 1, tzinfo=pytz.UTC)
            )

            # Determine type + name
            if isinstance(latest_record, Reservation):
                last_type = "reservation"
                name = latest_record.customer.customer_name
                email = latest_record.customer.email
                address = latest_record.customer.address
            elif isinstance(latest_record, Order):
                last_type = "order"
                name = latest_record.customer.customer_name
                email = latest_record.customer.email
                address= latest_record.customer.address
            elif isinstance(latest_record, CustomerService):
                last_type = "service"
                name = latest_record.customer.customer_name
                email = latest_record.customer.email
                address= latest_record.customer.address
            else:
                last_type = None
                name = None
                email=None
                address =None

            customer_data[phone] = {
                "name": name,
                "phone": phone,
                "email":email,
                "address":address,
                "most_recent_last": {
                    "type": last_type,
                    "created_at": latest_record.created_at if latest_record else None,
                },
                "total_create": res_count + order_count + service_count
            }

        data = sorted(
            [record for record in customer_data.values() if record['most_recent_last']['created_at']],
            key=lambda x: x["most_recent_last"]["created_at"],
            reverse=True
        )

        return Response(data)




class PendingCallbacksView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get all pending callbacks",
        operation_description="Returns a list of all customer service callbacks where `callback_done = False`.",
        responses={200: CustomerServiceSerializer(many=True)},
        tags=['Call Back']
    )
    def get(self, request):
        callbacks = CustomerService.objects.filter(type="callback", callback_done=False)
        serializer = CustomerServiceSerializer(callbacks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Update callback status",
        operation_description="Update the `callback_done` status of a customer service callback by ID.",
        manual_parameters=[
            openapi.Parameter('id', openapi.IN_PATH, description="Callback ID", type=openapi.TYPE_INTEGER),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'callback_done': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Mark callback as done or not")
            },
            required=['callback_done']
        ),
        responses={200: CustomerServiceSerializer()},
        tags=['Call Back']
    )
    
    def patch(self, request, *args, **kwargs):
        callback_id = kwargs.get("id")
        try:
            callback = CustomerService.objects.get(id=callback_id, type="callback")
        except CustomerService.DoesNotExist:
            return Response({"detail": "Callback not found"}, status=status.HTTP_404_NOT_FOUND)

        callback_done = request.data.get("callback_done")
        if callback_done is None:
            return Response({"detail": "callback_done field is required"}, status=status.HTTP_400_BAD_REQUEST)

        callback.callback_done = callback_done
        callback.save()

        serializer = CustomerServiceSerializer(callback)
        return Response(serializer.data, status=status.HTTP_200_OK)
    