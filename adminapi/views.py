from requests import request
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from accounts.models import User
from .serializers import  UserRestaurantSerializer,RestaurantSerializerList,RestaurantSerializerStatus,UserApprovalUpdateSerializer,CallSummarySerializer,RestaurantOrderSummarySerializer,TopSellingItemSerializer,RestaurantCallStatsSerializer,AdminApprovalSerializer
from restaurants.models import Restaurant,OpenAndCloseTime
from .serializers import RestaurantSerializer
from rest_framework.parsers import MultiPartParser, FormParser
from accounts.permissions import IsAdminRole
from accounts.translations import translate_text
from rest_framework.generics import CreateAPIView,RetrieveAPIView
from drf_yasg import openapi
from rest_framework.exceptions import ValidationError
from rest_framework import status , permissions
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from table.models import Table,Reservation
from order.models import Order
from subscription.models import Subscription
from django.db.models import Sum ,Q
from AIvapi.models import Assistance,CallInformations
from order.models import Order
from table.models import Reservation
from django.utils.dateparse import parse_date
from django.utils.timezone import now
from datetime import timedelta
from items.models import Item
from django.db.models import FloatField, Sum, OuterRef, Subquery
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
import calendar
from datetime import datetime
from django.db.models.functions import TruncMonth
from datetime import time


class AdminRegisterApiView(CreateAPIView):
    """
    API endpoint for registering a new user and creating a restaurant.
    Also provides JWT token upon successful registration.
    """
    queryset = User.objects.all()
    serializer_class = UserRestaurantSerializer
    permission_classes = [IsAdminRole]
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        tags=["Users"],
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

            data = RestaurantSerializer(restaurant).data

            if lean != 'EN':
                data['resturent_name'] = translate_text(restaurant.resturent_name, lean)
                data['address'] = translate_text(restaurant.address, lean)

            response_data = {
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
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


class Resturantpagination(PageNumberPagination):
    page_size = 10
    page_size_query_param ='page_size'




class AdminRestaurantListAPIView(APIView):
    permission_classes = [IsAdminRole]
    pagination_class = Resturantpagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['resturent_name']

    @swagger_auto_schema(
        operation_description="Retrieve a list of all restaurants (admin only).",
        tags=['Users'],
        responses={200: openapi.Response(
            description="List of restaurants",
            schema=RestaurantSerializerList(many=True)
        ),
        403: "Forbidden: Only admins can access this endpoint."
        },
    )

    def get(self, request):
        # Preload related objects to avoid N+1 queries
        restaurants = Restaurant.objects.select_related('ai_assistance', 'owner').all()
        search_value = request.query_params.get('search')
        
        filtered_restaurants = self.filter_queryset(restaurants, search_value)
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(filtered_restaurants, request)

        serializer = RestaurantSerializerList(page, many=True , context = {'request': request})
        return paginator.get_paginated_response(serializer.data)

    def filter_queryset(self, queryset, search_value):
        """
        Custom method to apply the search and filter.
        """
        if search_value:
            queryset = queryset.filter(resturent_name__icontains=search_value)
        return queryset




class AdminRestaurantDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve detailed information for a single restaurant by its ID (admin only).",
        manual_parameters=[
            openapi.Parameter(
                'id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description='Restaurant ID to retrieve'
            )
        ],
        responses={
            200: openapi.Response(
                description="Detailed restaurant information",
                schema=RestaurantSerializerList()
            ),
            400: "Bad Request: Missing or invalid ID.",
            404: "Not Found: Restaurant does not exist.",
            403: "Forbidden: Only admins can access this endpoint."
        },
        tags=['Users'],
    )
    def get(self, request):
        restaurant_id = request.query_params.get("id")
        if not restaurant_id:
            return Response({"error": "Restaurant ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            restaurant = Restaurant.objects.select_related('owner', 'ai_assistance').get(id=restaurant_id)
        except Restaurant.DoesNotExist:
            return Response({"error": "Restaurant not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = RestaurantSerializerList(restaurant)
        return Response(serializer.data, status=status.HTTP_200_OK)



class CustomPageNumberPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'




class ALLRestaurantStatus(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get all restaurants with optional search and filter: resturent_name, owner email, approved status.",
        tags=["Accounts"],
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description="Search by restaurant name or owner email (case-insensitive).",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'approved',
                openapi.IN_QUERY,
                description="Filter by owner approved status. Use 'true' or 'false'.",
                type=openapi.TYPE_BOOLEAN,
                required=False
            ),
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="Page number for pagination.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="Number of items per page (pagination).",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={200: RestaurantSerializerStatus(many=True)},
    )
    def get(self, request):
        search_query = request.query_params.get('search', '')
        approved_filter = request.query_params.get('approved', None)
        queryset = Restaurant.objects.all()
        if search_query:
            queryset = queryset.filter(
                Q(resturent_name__icontains=search_query) |
                Q(owner__email__icontains=search_query)
            )

        if approved_filter is not None:
            if approved_filter.lower() in ['true', '1']:
                queryset = queryset.filter(owner__approved=True)
            elif approved_filter.lower() in ['false', '0']:
                queryset = queryset.filter(owner__approved=False)
                
        paginator = CustomPageNumberPagination()
        paginated_qs = paginator.paginate_queryset(queryset, request)
        serializer = RestaurantSerializerStatus(paginated_qs, many=True , context = {'request': request})

        total_restaurant = Restaurant.objects.count()
        total_approved_restaurant = Restaurant.objects.filter(owner__approved=True).count()

        total_subscription = Subscription.objects.filter(is_active=True).count()

        total_revenue_subscription = Subscription.objects.filter(is_active=True).aggregate(
            total_revenue=Sum('price')
        )['total_revenue'] or 0

        response_data = {
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": serializer.data,
            "status": {
                "total_restaurant": total_restaurant,
                "total_approved_restaurant": total_approved_restaurant,
                "total_subscription": total_subscription,
                "total_revenue_subscription": float(total_revenue_subscription),  # convert Decimal to float for JSON
            }
        }

        return paginator.get_paginated_response(response_data)




class RestaurantStatusDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get detailed info of a single restaurant by ID including owner email, last login, and approved status.",
        responses={
            200: RestaurantSerializerStatus(),
            404: openapi.Response('Restaurant not found'),
        },
        tags=["Accounts"],
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_PATH,
                description="ID of the restaurant to retrieve",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
    )
    def get(self, request, id):
        try:
            restaurant = Restaurant.objects.get(id=id)
        except Restaurant.DoesNotExist:
            return Response({"detail": "Restaurant not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = RestaurantSerializerStatus(restaurant)
        return Response(serializer.data, status=status.HTTP_200_OK)
    



class UserApprovalUpdateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    approval_param = openapi.Parameter(
        name='approved',
        in_=openapi.IN_BODY,
        description='Boolean flag to approve or disapprove user',
        type=openapi.TYPE_BOOLEAN,
        required=True,
    )

    @swagger_auto_schema(
        operation_description="Update the approved status of a user (Admin only).",
        request_body=UserApprovalUpdateSerializer,
        responses={
            200: openapi.Response(description="User approval status updated successfully."),
            400: "Validation Error",
            404: "User not found",
            403: "Permission denied",
        },
        tags=["Accounts"]
    )

    def patch(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserApprovalUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "User approval status updated successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    



class CallSummaryAPIView(APIView):
    permission_classes = [IsAdminRole]

    @swagger_auto_schema(
        operation_description="Admin overview: total calls, minutes, orders, reservations, and revenue. Optional date filters.",
        manual_parameters=[
            openapi.Parameter(
                'date1', openapi.IN_QUERY,
                description="Start date (YYYY-MM-DD)", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                'date2', openapi.IN_QUERY,
                description="End date (YYYY-MM-DD)", type=openapi.TYPE_STRING, required=False
            ),
        ],
        responses={200: CallSummarySerializer},
        tags=["Overview Admin"]
    )
    def get(self, request):
        raw_date1 = request.query_params.get('date1')
        raw_date2 = request.query_params.get('date2')

        date1 = parse_date(raw_date1) if raw_date1 else None
        date2 = parse_date(raw_date2) if raw_date2 else None

        date_filter = Q()
        if date1 and date2:
            date_filter = Q(created_at__date__range=[date1, date2])
        elif date1:
            date_filter = Q(created_at__date__gte=date1)
        elif date2:
            date_filter = Q(created_at__date__lte=date2)


        call_qs = CallInformations.objects.filter(date_filter)
        total_call = call_qs.count()
        total_seconds = sum(
            float(d) for d in call_qs.values_list('duration_seconds', flat=True)
            if d and d.replace('.', '', 1).isdigit()
        )
        total_minute_use = total_seconds / 60

        #Orders
        order_qs = Order.objects.filter(date_filter)
        total_order = order_qs.count()

        # Reservations
        reservation_qs = Reservation.objects.filter(date_filter)
        total_reservations = reservation_qs.count()

        #Restaurant revenue (from orders)
        restaurants = Restaurant.objects.annotate(
            resturant_total_revinew=Sum(
                'orders__total_price',
                filter=Q(orders__created_at__range=(date1, date2)) if date1 and date2 else Q()
            )
        )   

        data = {
            "total_call": total_call,
            "total_minute_use": round(total_minute_use, 2),
            "total_order": total_order,
            "total_reservations": total_reservations,
        }

        return Response(data, status=status.HTTP_200_OK)




class TopSellingItemsAPIView(APIView):
    @swagger_auto_schema(
        operation_description="Get top 5 selling items in the last 30 days",
        responses={200: TopSellingItemSerializer(many=True)},
        tags=["Overview Admin"]
    )
    def get(self, request):
        thirty_days_ago = now() - timedelta(days=30)
        top_items = Item.objects.filter(
            order_items__order__created_at__gte=thirty_days_ago
        ).annotate(
            total_sells=Sum('order_items__quantity')
        ).order_by('-total_sells')[:5]

        serializer = TopSellingItemSerializer(top_items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'


class RestaurantCallStatsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    pagination_parameters = [
        openapi.Parameter(
            name='page',
            in_=openapi.IN_QUERY,
            description='Page number',
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            name='page_size',
            in_=openapi.IN_QUERY,
            description='Number of results per page (default is 10)',
            type=openapi.TYPE_INTEGER,
            required=False
        ),
    ]

    @swagger_auto_schema(
        operation_description="Get restaurant-wise total used minutes and total call cost.",
        manual_parameters=pagination_parameters,
        responses={200: RestaurantCallStatsSerializer(many=True)},
        tags=["Overview Admin"]
    )
    def get(self, request):
        call_subquery = CallInformations.objects.filter(
            assistant_id=OuterRef('assistant_id')
        ).annotate(
            secs=Cast('duration_seconds', FloatField())
        ).values('assistant_id').annotate(
            total_secs=Sum('secs'),
            total_cost=Sum('cost')
        )

        qs = Assistance.objects.annotate(
            total_seconds=Subquery(call_subquery.values('total_secs')[:1]),
            total_cost=Subquery(call_subquery.values('total_cost')[:1])
        ).filter(total_seconds__isnull=False)

        stats = []
        for ass in qs:
            restaurant = ass.restaurant
            total_seconds = ass.total_seconds or 0
            total_minutes = round(total_seconds / 60.0, 2)
            cost = ass.total_cost or 0
            stats.append({
                'resturent_name': restaurant.resturent_name,
                'image': restaurant.image,
                'total_used_minute': total_minutes,
                'total_cost': cost
            })

        
        paginator = StandardResultsSetPagination()
        paginated_stats = paginator.paginate_queryset(stats, request)

        serializer = RestaurantCallStatsSerializer(paginated_stats, many=True , context = {'request': request})
        return paginator.get_paginated_response(serializer.data)



class AdminApprovalUpdateView(APIView):

    permission_classes = [IsAdminRole]

    @swagger_auto_schema(
        operation_description="Get the adminapproved status of the currently authenticated user.",
        responses={200: AdminApprovalSerializer},
        tags=["Admin approval"]
    )
    def get(self, request):
        user = request.user
        serializer = AdminApprovalSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Update the adminapproved field of the currently authenticated user.",
        request_body=AdminApprovalSerializer,
        responses={
            200: AdminApprovalSerializer,
            400: 'Bad Request',
        },
        tags=["Admin approval"]
    )
    def patch(self, request):
        user = request.user
        serializer = AdminApprovalSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Admin approval status updated successfully.",
                "user": serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class MonthlyRevenueAPIView(APIView):

    @swagger_auto_schema(
        operation_description="Get monthly revenue for the current year.",
        responses={200: openapi.Response(
            description="Monthly revenue",
            examples={
                "application/json": {
                    "jan": 1000.0,
                    "feb": 800.0,
                    "mar": 0.0,
                    "apr": 50.0,
                    "may": 200.0,
                    "jun": 300.0,
                    "jul": 0.0,
                    "aug": 0.0,
                    "sep": 0.0,
                    "oct": 0.0,
                    "nov": 0.0,
                    "dec": 0.0
                }
            }
        )},
        tags=["Overview Admin"]
    )

    def get(self, request):
        current_year = datetime.now().year

        monthly_data = (
            Subscription.objects.filter(
                price__isnull=False,
                created_at__year=current_year
            )
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(total_revenue=Sum('price'))
            .order_by('month')
        )

        revenue = {
            month.lower(): 0.0 for month in [
                'jan', 'feb', 'mar', 'apr', 'may', 'jun',
                'jul', 'aug', 'sep', 'oct', 'nov', 'dec'
            ]
        }

        for data in monthly_data:
            month_index = data['month'].month 
            month_name = calendar.month_abbr[month_index].lower()
            revenue[month_name] = float(data['total_revenue'])

        return Response(revenue)
    




class RestaurantAnalysis(APIView):
    permission_classes = [IsAdminRole]


    @swagger_auto_schema(
        operation_summary="Get Restaurant Statistics (Admin Only)",
        operation_description=(
            "Returns a list of all restaurants with aggregated statistics:\n"
            "- total_subscription_price: Sum of active subscriptions for the restaurant owner.\n"
            "- total_order_revenue: Total revenue from all orders linked to the restaurant.\n"
            "- total_reservation_count: Total number of reservations made for that restaurant."
        ),
        responses={
            200: openapi.Response(
                description="List of restaurant statistics",
                examples={
                    "application/json": [
                        {
                            "restaurant_name": "Pizza World",
                            "owner_email": "owner1@example.com",
                            "total_subscription_price": 49.99,
                            "total_order_revenue": 1250.50,
                            "total_reservation_count": 17
                        }
                    ]
                },
            ),
            403: "Permission denied (Admin only)",
        },
        tags=["Overview Admin"]
    )
    def get(self, request):
        data = []

        restaurants = Restaurant.objects.select_related('owner').all()

        for restaurant in restaurants:
            # total order revenue
            total_order_revenue = (
                Order.objects.filter(restaurant=restaurant)
                .aggregate(total=Sum('total_price'))['total'] or 0
            )

            # total subscription price for that restaurant owner
            total_subscription_price = (
                Subscription.objects.filter(user=restaurant.owner)
                .aggregate(total=Sum('price'))['total'] or 0
            )

            # total reservation count for that restaurant
            total_reservation_count = (
                Reservation.objects.filter(table__restaurant=restaurant).count()
            )

            data.append({
                "restaurant_name": restaurant.resturent_name,
                "owner_email": restaurant.owner.email,
                "total_subscription_price": float(total_subscription_price),
                "total_order_revenue": float(total_order_revenue),
                "total_reservation_count": total_reservation_count,
            })

        return Response(data, status=status.HTTP_200_OK)

