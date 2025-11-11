from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, serializers
from .models import AreaManagement
from .serializers import AreaManagementSerializar
from restaurants.models import Restaurant
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class AreaManagementListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        operation_summary="List all AreaManagement records for the logged-in user's restaurant",
        operation_description="Returns all delivery area settings for the restaurant owned by the authenticated user.",
        responses={
            200: AreaManagementSerializar(many=True),
            404: openapi.Response("Restaurant not found")
        },
        tags=['Area Managemen']
    )
    def get(self, request):
        restaurant = Restaurant.objects.filter(owner=request.user).first()
        if not restaurant:
            return Response({"error": "You don't have a restaurant."}, status=status.HTTP_404_NOT_FOUND)

        areas = AreaManagement.objects.filter(restaurant=restaurant)
        serializer = AreaManagementSerializar(areas, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Create a new AreaManagement for the logged-in user's restaurant",
        operation_description=(
            "Allows a restaurant owner to create a new delivery area (postal code, delivery time, and fee). "
            "The `restaurant` field is automatically assigned based on the logged-in user."
        ),
        request_body=AreaManagementSerializar,
        responses={
            201: AreaManagementSerializar,
            400: openapi.Response("Invalid data or restaurant not found")
        },
        tags=['Area Managemen']
    )
    def post(self, request):
        restaurant = Restaurant.objects.filter(owner=request.user).first()
        if not restaurant:
            return Response({"error": "You don't have a restaurant."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AreaManagementSerializar(data=request.data)
        if serializer.is_valid():
            serializer.save(restaurant=restaurant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AreaManagementDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return AreaManagement.objects.get(pk=pk, restaurant__owner=user)
        except AreaManagement.DoesNotExist:
            return None

    @swagger_auto_schema(
        operation_summary="Retrieve a specific AreaManagement record",
        operation_description="Fetch a single AreaManagement entry belonging to the logged-in user's restaurant.",
        responses={
            200: AreaManagementSerializar,
            404: openapi.Response("Area not found or unauthorized")
        },
        tags=['Area Managemen']
    )
    def get(self, request, pk):
        area = self.get_object(pk, request.user)
        if not area:
            return Response({"error": "Area not found or unauthorized."}, status=status.HTTP_404_NOT_FOUND)
        serializer = AreaManagementSerializar(area)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Partially update an AreaManagement record",
        operation_description="Allows partial updates (PATCH) to an AreaManagement record belonging to the user's restaurant.",
        request_body=AreaManagementSerializar,
        responses={
            200: AreaManagementSerializar,
            400: openapi.Response("Invalid input"),
            404: openapi.Response("Area not found or unauthorized")
        },
        tags=['Area Managemen']
    )
    def patch(self, request, pk):
        area = self.get_object(pk, request.user)
        if not area:
            return Response({"error": "Area not found or unauthorized."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AreaManagementSerializar(area, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Delete an AreaManagement record",
        operation_description="Deletes an AreaManagement record belonging to the authenticated user's restaurant.",
        responses={
            204: openapi.Response("Area deleted successfully"),
            404: openapi.Response("Area not found or unauthorized")
        },
        tags=['Area Managemen']
    )
    def delete(self, request, pk):
        area = self.get_object(pk, request.user)
        if not area:
            return Response({"error": "Area not found or unauthorized."}, status=status.HTTP_404_NOT_FOUND)

        area.delete()
        return Response({"message": "Area deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


