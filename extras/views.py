from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from .models import Extra
from .serializers import ExtraSerializer
from restaurants.models import Restaurant
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser


from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi




class ExtraViewSet(viewsets.ModelViewSet):
    serializer_class = ExtraSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    pagination_class=None

    def get_queryset(self):
        return Extra.objects.filter(restaurant__owner=self.request.user)
    

    @swagger_auto_schema(
        operation_description="Create a new extra for the restaurant owned by the authenticated user.",
        request_body=ExtraSerializer,
        responses={
            201: openapi.Response("Extra created successfully", ExtraSerializer),
            400: "Invalid data",
            401: "Unauthorized",
        },
        tags=["Restaurant Extras"]
    )
    def create(self, request, *args, **kwargs):
        restaurant = Restaurant.objects.get(owner=request.user)
        serializer = ExtraSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(restaurant=restaurant)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    
    @swagger_auto_schema(
        operation_description="List all extras for the restaurant owned by the authenticated user.",
        responses={200: ExtraSerializer(many=True)},
        tags=["Restaurant Extras"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    

    @swagger_auto_schema(
        operation_description="Retrieve a specific extra by ID.",
        responses={200: ExtraSerializer()},
        tags=["Restaurant Extras"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    

    @swagger_auto_schema(
        operation_description="Partially update an extra.",
        request_body=ExtraSerializer,
        responses={200: ExtraSerializer()},
        tags=["Restaurant Extras"]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete an extra.",
        responses={204: "Deleted successfully"},
        tags=["Restaurant Extras"]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)