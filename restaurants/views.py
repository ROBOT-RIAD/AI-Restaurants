from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import OpenAndCloseTime, Restaurant
from .serializers import OpenAndCloseTimeSealizer
from accounts.permissions import IsOwnerRole




class OpenAndCloseTimeAPIView(APIView):
    permission_classes = [IsOwnerRole]

    @swagger_auto_schema(
        operation_summary="List all open/close times for the owner's restaurant",
        responses={200: OpenAndCloseTimeSealizer(many=True)},
        tags=['Open and Close Times']
    )
    def get(self, request):
        """List all open/close times for the authenticated owner's restaurant"""
        try:
            restaurant = Restaurant.objects.get(owner=request.user)
        except Restaurant.DoesNotExist:
            return Response({"detail": "Restaurant not found for this owner."},
                            status=status.HTTP_404_NOT_FOUND)

        open_close_times = OpenAndCloseTime.objects.filter(restaurant=restaurant)
        serializer = OpenAndCloseTimeSealizer(open_close_times, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Create a new open/close time for the owner's restaurant",
        request_body=OpenAndCloseTimeSealizer,
        responses={201: OpenAndCloseTimeSealizer()},
        tags=['Open and Close Times']
    )
    def post(self, request):
        """Create a new open/close time (ensures no duplicate day_of_week)"""
        try:
            restaurant = Restaurant.objects.get(owner=request.user)
        except Restaurant.DoesNotExist:
            return Response({"detail": "Restaurant not found for this owner."},
                            status=status.HTTP_404_NOT_FOUND)

        day_of_week = request.data.get("day_of_week")

        # Prevent duplicate day_of_week for the same restaurant
        if OpenAndCloseTime.objects.filter(restaurant=restaurant, day_of_week=day_of_week).exists():
            return Response({"detail": f"Open/close time for '{day_of_week}' already exists."},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = OpenAndCloseTimeSealizer(data=request.data)
        if serializer.is_valid():
            serializer.save(restaurant=restaurant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





class OpenAndCloseTimeDetailAPIView(APIView):
    permission_classes = [IsOwnerRole]

    def get_object(self, request, pk):
        try:
            restaurant = Restaurant.objects.get(owner=request.user)
            return OpenAndCloseTime.objects.get(pk=pk, restaurant=restaurant)
        except (Restaurant.DoesNotExist, OpenAndCloseTime.DoesNotExist):
            return None

    @swagger_auto_schema(
        operation_summary="Retrieve a single open/close record",
        responses={200: OpenAndCloseTimeSealizer()},
        tags=['Open and Close Times']
    )
    def get(self, request, pk):
        """Get a specific open/close time entry"""
        obj = self.get_object(request, pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = OpenAndCloseTimeSealizer(obj)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Partially update an existing open/close record",
        request_body=OpenAndCloseTimeSealizer,
        responses={200: OpenAndCloseTimeSealizer()},
        tags=['Open and Close Times']
    )
    def patch(self, request, pk):
        """Update part of an open/close record"""
        obj = self.get_object(request, pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = OpenAndCloseTimeSealizer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Delete an open/close record",
        responses={204: 'Deleted successfully'},
        tags=['Open and Close Times']
    )
    def delete(self, request, pk):
        """Delete an open/close record"""
        obj = self.get_object(request, pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response({"detail": "Deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
    





