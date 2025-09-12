from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .serializers import UserRestaurantSerializerInfo,RestaurantSerializerInfo
from restaurants.models import Restaurant
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from accounts.translations import translate_text
from rest_framework.parsers import MultiPartParser, FormParser
from accounts.permissions import IsOwnerRole


class UserRestaurantDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Retrieve user restaurant details",
        responses={200: UserRestaurantSerializerInfo},
        tags=['Restaurant'],
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
    def get(self, request, *args, **kwargs):
        lean = request.query_params.get('lean', 'EN').upper()
        user = request.user
        
        user_serializer = UserRestaurantSerializerInfo(user,context ={'request': request})
        
        if lean != 'EN' and user_serializer.data.get('restaurant'):
            restaurant_data = user_serializer.data['restaurant']
            
            if 'resturent_name' in restaurant_data:
                restaurant_data['resturent_name'] = translate_text(restaurant_data['resturent_name'], lean)
            
            if 'address' in restaurant_data:
                restaurant_data['address'] = translate_text(restaurant_data['address'], lean)
        
        return Response(user_serializer.data)
    



class UpdateRestaurantInfo(APIView):
    permission_classes = [IsAuthenticated,IsOwnerRole]
    parser_classes = (MultiPartParser, FormParser)
    @swagger_auto_schema(
        operation_description="Update the authenticated user's restaurant information.",
        request_body=RestaurantSerializerInfo,
        responses={
            200: RestaurantSerializerInfo,
            400: 'Bad Request - Validation errors',
            404: 'No restaurant found for this user'
        },
        tags=['Restaurant'],
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
    def patch(self, request, *args, **kwargs):
        lean = request.query_params.get('lean', 'EN').upper()
        user = request.user
        try:
            restaurant = user.restaurants.first()
        except Restaurant.DoesNotExist:
            return Response({"error": "No restaurant found for this user."}, status=status.HTTP_404_NOT_FOUND)
        
        if lean != 'EN':
            resturent_name = request.data.get('resturent_name')
            address = request.data.get('address')

            if resturent_name:
                request.data['resturent_name'] = translate_text(resturent_name, 'EN')
            if address:
                request.data['address'] = translate_text(address, 'EN')

        serializer = RestaurantSerializerInfo(
            restaurant, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            data =serializer.data
            if lean != 'EN':
                data['resturent_name'] = translate_text(data['resturent_name'], lean)
                data['address'] = translate_text(data['address'], lean)
            return Response(data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
