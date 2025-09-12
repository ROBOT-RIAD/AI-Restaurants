from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions,generics
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import OrderCreateSerializer,OrderUpdateSerializer,OrderSerializer,CustomerOrderGroupSerializer
from .models import Order
from restaurants.models import Restaurant


class OrderCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Create a new order with order items",
        request_body=OrderCreateSerializer,
        responses={201: OrderCreateSerializer, 400: "Validation Error"},
        tags=["Orders"]
    )
    def post(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data)
        if serializer.is_valid():
            order = serializer.save()
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




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
            return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class RestaurantOrdersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve all orders for the logged-in user's restaurant, "
                              "including order items and full item details.",
        responses={200: OrderSerializer(many=True)},
        tags=["Orders"],
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        lean = request.query_params.get('lean')  
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
                schema=CustomerOrderGroupSerializer(many=True)  # ✅ use serializer
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
        orders = Order.objects.filter(restaurant__in=restaurants, phone=phone)

        if not orders.exists():
            return Response({"error": "No orders found"}, status=404)

        serializer = CustomerOrderGroupSerializer({"orders": orders})
        return Response(serializer.data, status=200)




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
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


