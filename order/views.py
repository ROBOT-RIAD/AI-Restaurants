from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions,generics
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import OrderCreateSerializer,OrderUpdateSerializer,OrderSerializer,CustomerOrderGroupSerializer,OrderVerificationSerializer
from .models import Order
from restaurants.models import Restaurant
from django.db.models import Sum, Count
from datetime import timedelta
from django.utils import timezone
from django.utils.timezone import now
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from .emails import send_order_confirmation_email
from accounts.serializers import RestaurantSerializer
from datetime import datetime
from table.models import Reservation
from customerService.models import CustomerService
from table.serializers import ReservationSerializer
from customerService.serializers import CustomerServiceSerializer





class OrderCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Create a new order with order items",
        request_body=OrderCreateSerializer,
        responses={201: OrderCreateSerializer, 400: "Validation Error"},
        tags=["Orders"]
    )
    def post(self, request, *args, **kwargs):
        # print("Request data: =========================================>", request.data)

        serializer = OrderCreateSerializer(data=request.data)

        if serializer.is_valid():
            order = serializer.save()
            data = OrderSerializer(order).data

            channel_layer = get_channel_layer()

            async_to_sync(channel_layer.group_send)(
                f"restaurant_{order.restaurant.id}",  # Assuming `order.restaurant` is set
                {
                    "type": "order_created",
                    "order": data
                }
            )

            return Response(data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class OrderAutoVerifyView(APIView):
    """
    Public endpoint: verifies order and displays all order info.
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Auto-verify an order by ID (public)",
        operation_description=(
            "When this endpoint is visited (e.g. via email link), "
            "it automatically verifies the order (sets `verified=True` if not yet verified) "
            "and returns an HTML confirmation page with full order details."
        ),
        tags=["Orders"],
        manual_parameters=[
            openapi.Parameter(
                "pk",
                openapi.IN_PATH,
                description="Order ID (primary key)",
                type=openapi.TYPE_INTEGER,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(
                description="HTML confirmation page showing full order info"
            ),
            404: "Order not found",
        },
    )
    def get(self, request, pk):

        order = get_object_or_404(Order, pk=pk)

        # If not verified yet → mark as verified
        if not order.verified:
            order.verified = True
            order.save()


        serializer = OrderSerializer(order)
        data = serializer.data
        
        restaurant = get_object_or_404(Restaurant, pk=data["restaurant"])
        Delivery_Area = data["delivery_area_json"]

        html = f"""
        <html>
        <head>
            <title>Order Confirmation</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f8f9fa;
                    padding: 40px;
                    color: #333;
                }}
                .container {{
                    max-width: 700px;
                    margin: 0 auto;
                    background: white;
                    padding: 25px;
                    border-radius: 12px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h2 {{
                    text-align: center;
                    color: green;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                th, td {{
                    border: 1px solid #ccc;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f1f1f1;
                }}
                .footer {{
                    margin-top: 25px;
                    text-align: center;
                    font-size: 14px;
                    color: gray;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>✅ Thank you, {data["customer_name"]}! Your order has been verified.</h2>
                <h3>Order Details</h3>
                <p><b>Order ID:</b> {data["id"]}</p>
                <p><b>Status:</b> {data["order_type"]}</p>
                <p><b>Total Price:</b> ${data["total_price"]}</p>
                <p><b>Phone:</b> {data["phone"] or "N/A"}</p>
                <p><b>Email:</b> {data["email"] or "N/A"}</p>
                <p><b>Address:</b> {data["address"] or "N/A"}</p>
                <p><b>Notes:</b> {data["order_notes"] or "None"}</p>
                <p><b>Allergy Info:</b> {data["allergy"] or "None"}</p>

                <h3>Order Items</h3>
                <table>
                    <tr>
                        <th>Item</th>
                        <th>Quantity</th>
                        <th>Extras</th>
                        <th>Extras Price</th>
                        <th>Item Price</th>
                        <th>Discount</th>
                        <th>Total Price</th>
                    </tr>
        """
        if data["order_type"] == "delivery" and data.get("delivery_area_json"):
            area = data["delivery_area_json"]
            html += f"""
                <h3>Delivery Area</h3>
                <p><b>Postal Code:</b> {area.get("postalcode") or "N/A"}</p>
                <p><b>Estimated Delivery Time:</b> {area.get("estimated_delivery_time") or "N/A"}</p>
                <p><b>Delivery Fee:</b> {area.get("delivery_fee") or "N/A"}</p>
            """

        for item in data["order_items"]:
            item_json = item["item_json"]
            html += f"""
                    <tr>
                        <td>{item["item_json"].get("item_name") if item["item_json"] else "Unknown"}</td>
                        <td>{item["quantity"]}</td>
                        <td>{item["extras"] or "None"}</td>
                        <td>{item["extras_price"] or "None"}</td>
                        <td>${item_json["price"]}</td>
                        <td>{item_json["discount"] or "0"} %</td>
                        <td>${item["price"]}</td>
                    </tr>
            """

        html += f"""
                </table>
                <div class="footer">
                    <p><b>@{restaurant.resturent_name}</b></p>
                    <p><b>{restaurant.phone_number_1}</b></p>
                    <p>Verified on: {data["updated_at"]}</p>
                </div>
            </div>
        </body>
        </html>
        """

        
        send_order_confirmation_email(order)
        return HttpResponse(html)




class OrderUpdateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Partially update an order",
        request_body=OrderUpdateSerializer,
        responses={200: OrderUpdateSerializer, 400: "Validation Error", 404: "Not Found"},
        tags=["Orders"]
    )
    def patch(self, request, pk, *args, **kwargs):
        try:
            order = Order.objects.get(pk=pk, restaurant__owner=request.user)
        except Order.DoesNotExist:
            return Response({"error": "Order not found or not allowed"}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderUpdateSerializer(order, data=request.data, partial=True)
        if serializer.is_valid():
            order = serializer.save()
            data = OrderSerializer(order).data

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"restaurant_{order.restaurant.id}",
                {
                    "type": "order_updated",
                    "order": data
                }
            )

            return Response(data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class RestaurantOrdersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve all orders for the logged-in user's restaurant, "
                              "including order items and full item details.",
        responses={200: OrderSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="Filter orders by date (format: YYYY-MM-DD)",
                type=openapi.TYPE_STRING,
                required=False
            ),
        ],
        tags=["Orders"],
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        lean = request.query_params.get('lean')
        date_str = request.query_params.get('date')  
        try:
            restaurant = Restaurant.objects.get(owner=user)
        except Restaurant.DoesNotExist:
            return Response(
                {"error": "You don't have a restaurant assigned."},
                status=status.HTTP_400_BAD_REQUEST
            )

        orders = (
            Order.objects.filter(restaurant=restaurant)
            .prefetch_related("order_items__item")
        )

        if date_str:
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                orders = orders.filter(created_at__date=date_obj)
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

    

class OrderDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve a single order by ID for the logged-in user's restaurant, "
                              "including order items and full item details.",
        responses={200: OrderSerializer, 404: "Not Found"},
        tags=["Orders"],
    )
    def get(self, request, pk, *args, **kwargs):
        try:
            order = Order.objects.prefetch_related("order_items__item").get(
                pk=pk, restaurant__owner=request.user
            )
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found or not allowed"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)




class CustomerOrdersByPhoneAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Get all orders for a customer by phone number (only within restaurants owned by the authenticated user).",
        manual_parameters=[
            openapi.Parameter(
                'phone',
                openapi.IN_QUERY,
                description="Customer phone number",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="List of customer orders with aggregated customer info",
                schema=CustomerOrderGroupSerializer(many=True) 
            ),
            400: "Phone number is required",
            401: "Unauthorized",
        },
        tags=["customer Api"]
    )
    def get(self, request):
        phone = request.query_params.get("phone")
        if not phone:
            return Response({"error": "Phone number is required"}, status=400)

        restaurants = Restaurant.objects.filter(owner=request.user)
        orders = Order.objects.filter(restaurant__in=restaurants, customer__phone=phone)
        reservations = Reservation.objects.filter(table__restaurant__in=restaurants, customer__phone=phone)
        services = CustomerService.objects.filter(restaurant__in=restaurants, customer__phone=phone)


        if not orders.exists():
            return Response({"error": "No orders found"}, status=404)

        serializer = CustomerOrderGroupSerializer({"orders": orders})
        return Response({
            "orders": serializer.data,
            "reservations": ReservationSerializer(reservations, many=True).data,
            "services": CustomerServiceSerializer(services, many=True).data,
        }, status=200)




class PublicOrderCreateAPIView(APIView):
    """
    Public API endpoint to create an order (no login required).
    """
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_description="Public API: Create a new order with order items (no authentication required).",
        request_body=OrderCreateSerializer,
        responses={201: OrderSerializer, 400: "Validation Error"},
        tags=["Webhook"]
    )
    def post(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data)
        if serializer.is_valid():
            order = serializer.save()
            data = OrderSerializer(order).data

            channel_layer = get_channel_layer()

            async_to_sync(channel_layer.group_send)(
                f"restaurant_{order.restaurant.id}",
                {
                    "type": "order_created",
                    "order": data
                }
            )
            return Response(data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    



class RestaurantOrderStatsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get the total revenue and total orders, as well as daily revenue and order statistics for the last 7 days for the restaurant of the authenticated user.",
        responses={
            200: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "status": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "total_revenue": openapi.Schema(type=openapi.TYPE_NUMBER, format=openapi.FORMAT_DECIMAL),
                                "total_orders": openapi.Schema(type=openapi.TYPE_INTEGER),
                            },
                        ),
                        "last_7_days_revenue": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                additionalProperties=openapi.Schema(type=openapi.TYPE_NUMBER, format=openapi.FORMAT_DECIMAL),
                            ),
                        ),
                        "last_7_days_orders": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                additionalProperties=openapi.Schema(type=openapi.TYPE_INTEGER),
                            ),
                        ),
                    },
                ),
            ),
            404: openapi.Response(
                description="Restaurant not found or no orders",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
        tags=["Overview"]
    )

    def get(self, request):
        # Get the user's restaurants
        restaurants = Restaurant.objects.filter(owner=request.user)

        if not restaurants:
            return Response({"error": "No restaurants found for this user."}, status=status.HTTP_404_NOT_FOUND)

        # Filter orders by user's restaurant
        orders = Order.objects.filter(restaurant__in=restaurants)

        # Calculate total revenue and total orders
        total_revenue = orders.aggregate(total_revenue=Sum('total_price'))['total_revenue'] or 0
        total_orders = orders.count()

        # Get the last 7 days from today
        today = timezone.now().date()
        last_7_days = [today - timedelta(days=i) for i in range(7)]

        # Initialize revenue and order counts for the last 7 days
        last_7_days_revenue = []
        last_7_days_orders = []

        # Loop through the last 7 days and calculate daily statistics
        for day in last_7_days:
            daily_orders = orders.filter(created_at__date=day)
            daily_revenue = daily_orders.aggregate(daily_revenue=Sum('total_price'))['daily_revenue'] or 0
            daily_order_count = daily_orders.count()

            # Append the results for this day
            last_7_days_revenue.append({f"day{7 - (today - day).days}": daily_revenue})
            last_7_days_orders.append({f"day{7 - (today - day).days}": daily_order_count})

        # Return the response
        return Response({
            "status": {
                "total_revenue": total_revenue,
                "total_orders": total_orders
            },
            "last_7_days_revenue": last_7_days_revenue,
            "last_7_days_orders": last_7_days_orders
        })





class RestaurantSingleOrderView(APIView):
    """
    Retrieve a single order by ID for the logged-in user's restaurant.
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve a single order (with items and item details) "
                              "for the logged-in restaurant owner by order ID.",
        responses={200: OrderSerializer()},
        tags=["Orders"],
    )
    def get(self, request, pk, *args, **kwargs):
        user = request.user

        # Ensure user owns a restaurant
        try:
            restaurant = Restaurant.objects.get(owner=user)
        except Restaurant.DoesNotExist:
            return Response(
                {"error": "You don't have a restaurant assigned."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch the order belonging to this restaurant
        order = get_object_or_404(
            Order.objects.prefetch_related("order_items__item"),
            pk=pk,
            restaurant=restaurant
        )

        order_data = OrderSerializer(order).data
        restaurant_data = RestaurantSerializer(restaurant).data
        send_data = {
            "id": restaurant_data['id'],
            "resturent_name": restaurant_data['resturent_name'],
            "address": restaurant_data['address'],
            "phone_number_1": restaurant_data['phone_number_1'],
            "twilio_number": restaurant_data['twilio_number'],
            "opening_time": restaurant_data['opening_time'],
            "closing_time": restaurant_data['closing_time'],
            "website": restaurant_data['website'],
            "image": restaurant_data['image']
        }
        order_data["restaurant"] = send_data
        return Response(order_data, status=status.HTTP_200_OK)





