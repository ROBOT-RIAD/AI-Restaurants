from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from restaurants.models import Restaurant
from django.db.models import Q

from .models import Customer
from .serializers import CustomerSerializer
from accounts.permissions import IsOwnerRole

#swagger
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.exceptions import PermissionDenied



class CustomerViewSet(ModelViewSet):
    """
    ViewSet for managing customers.
    Owners can only see and create customers for their own restaurants.
    """
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated, IsOwnerRole]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["phone", "customer_name"]
    search_fields = ["customer_name", "phone"]

    def get_queryset(self):
        user = self.request.user
        return Customer.objects.filter(
            Q(orders__restaurant__owner=user) |
            Q(reservations__table__restaurant__owner=user) |
            Q(services__restaurant__owner=user)
        ).distinct().order_by('-id')


    def perform_create(self, serializer):
        user = self.request.user
        restaurant_id = self.request.data.get("restaurant")
        if not restaurant_id:
            raise PermissionDenied("Restaurant ID is required.")

        restaurant = Restaurant.objects.filter(id=restaurant_id, owner=user).first()
        if not restaurant:
            raise PermissionDenied("You do not own this restaurant.")

        serializer.save()

    @swagger_auto_schema(
        operation_summary="List all customers",
        operation_description="Returns a list of customers with search and filtering options.",
        tags=["Customer"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a new customer",
        tags=["Customer"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a customer by ID",
        tags=["Customer"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partially update a customer (PATCH)",
        tags=["Customer"]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete a customer",
        tags=["Customer"]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
