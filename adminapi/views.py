from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from accounts.models import User
from .serializers import  UserRestaurantSerializer
from restaurants.models import Restaurant
from .serializers import RestaurantSerializer
from rest_framework.parsers import MultiPartParser, FormParser
from accounts.permissions import IsAdminRole
from accounts.translations import translate_text
from rest_framework.generics import CreateAPIView
from drf_yasg import openapi
from rest_framework.exceptions import ValidationError
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from table.models import Table


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
            schema=RestaurantSerializer(many=True)
        ),
        403: "Forbidden: Only admins can access this endpoint."
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

    def get(self, request):
        lean = request.query_params.get('lean')
        restaurants = Restaurant.objects.all()
        search_value = request.query_params.get('search')
        if search_value and lean != 'EN':
            search_value = translate_text(search_value, 'EN')
        
        filtered_restaurants = self.filter_queryset(restaurants, search_value)
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(filtered_restaurants, request)
        
        serializer = RestaurantSerializer(page, many=True)
        data = serializer.data
    
        if lean != 'EN':
            for restaurant in data:
                if restaurant.get('resturent_name'):
                    restaurant['resturent_name'] = translate_text(restaurant['resturent_name'], lean)
                if restaurant.get('address'):
                    restaurant['address'] = translate_text(restaurant['address'], lean)
                
        return paginator.get_paginated_response(data)
    
    def filter_queryset(self, queryset, search_value):
        """
        Custom method to apply the search and filter.
        """
        if search_value:
            queryset = queryset.filter(resturent_name__icontains=search_value)
        
        return queryset






