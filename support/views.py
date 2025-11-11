from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from .models import Support
from .serializers import SupportSerializer,SupportSerializerGet,SupportStatusUpdateSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.parsers import MultiPartParser, FormParser
from restaurants.models import Restaurant
from django.shortcuts import get_object_or_404
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# Create your views here.

class CreateSupportView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        operation_description="Create a new support ticket for the authenticated user's restaurant.",
        request_body=SupportSerializer,
        responses={
            201: openapi.Response(
                description="Support ticket created successfully",
                schema=SupportSerializer
            ),
            400: openapi.Response(
                description="Bad request (missing required fields or invalid data)"
            ),
            401: openapi.Response(
                description="Unauthorized (authentication required)"
            ),
        },
        tags=['Support']
    )

    def post(self, request, *args, **kwargs):
        """
        API endpoint to create a new support ticket for the authenticated user's restaurant.
        """
        
        try:
            # Get the restaurant of the authenticated user
            restaurant = Restaurant.objects.get(owner=request.user)
        except Restaurant.DoesNotExist:
            return Response(
                {"detail": "User does not have an associated restaurant."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        print(restaurant)
        
        # Retrieve the required fields from the request data
        issue = request.data.get('issue')
        issue_details = request.data.get('issue_details')
        uploaded_file = request.FILES.get('uploaded_file')
        
        # Check if required fields are provided
        if not issue or not issue_details:
            return Response(
                {"detail": "Issue and issue details are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Prepare data for the serializer
        data = {
            'issue': issue,
            'issue_details': issue_details,
            'uploaded_file': uploaded_file
        }

        # Create and validate the serializer
        serializer = SupportSerializer(data=data , context={'request': request})
        
        if serializer.is_valid():
            support = serializer.save(restaurant=restaurant)

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"restaurant_{restaurant.id}",
                {
                    "type": "support_created",
                    "support": SupportSerializer(support, context={'request': request}).data
                }
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        # Return errors if the serializer is invalid
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class SupportListAPIView(APIView):
    permission_classes =[IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve support tickets. Filter by status and search by restaurant name.",
        manual_parameters=[
            openapi.Parameter(
                'status', openapi.IN_QUERY,
                description="Filter by support status (e.g., 'pending', 'resolved')",
                type=openapi.TYPE_STRING,
                enum=['pending', 'resolved'],
                required=False
            ),
            openapi.Parameter(
                'restaurant_name', openapi.IN_QUERY,
                description="Search by restaurant name (case-insensitive, partial match)",
                type=openapi.TYPE_STRING,
                required=False
            ),
        ],
        responses={200: SupportSerializer(many=True)},
        tags=['Support']
    )
    def get(self, request):
        status_param = request.query_params.get('status')
        restaurant_name = request.query_params.get('restaurant_name')

        supports = Support.objects.all().order_by('-created_at')

        if status_param:
            supports = supports.filter(status=status_param)

        if restaurant_name:
            supports = supports.filter(restaurant__resturent_name__icontains=restaurant_name)

        serializer = SupportSerializerGet(supports, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    


class SupportDetailAPIView(APIView):
    @swagger_auto_schema(
        operation_description="Retrieve a single support ticket by ID.",
        responses={
            200: SupportSerializer(),
            404: 'Not Found'
        },
        tags=["Support"]
    )
    def get(self, request, pk):
        support = get_object_or_404(Support, pk=pk)
        serializer = SupportSerializerGet(support , context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    



class SupportStatusUpdateAPIView(APIView):
    permission_classes =[IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Update the status of a support ticket.",
        request_body=SupportStatusUpdateSerializer,
        responses={
            200: SupportStatusUpdateSerializer,
            400: 'Bad Request',
            404: 'Not Found'
        },
        tags=["Support"]
    )
    def patch(self, request, pk):
        support = get_object_or_404(Support, pk=pk)
        serializer = SupportStatusUpdateSerializer(support, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            data = SupportSerializerGet(support, context={'request': request}).data
            restaurant_id = support.restaurant.id
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"restaurant_{restaurant_id}",
                {
                    "type": "support_updated",
                    "support": data
                }
            )
            return Response(data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
