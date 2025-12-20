from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from restaurants.models import Restaurant

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
        """
        Return only customers belonging to restaurants owned by the logged-in user.
        """
        user = self.request.user
        return Customer.objects.filter(
            restaurant__owner=user
        ).order_by('-id')

    def perform_create(self, serializer):
        """
        Ensure that a new customer is always linked to a restaurant owned by the logged-in user.
        """
        user = self.request.user
        # Get all restaurants owned by this user
        restaurants = Restaurant.objects.filter(owner=user)
        if not restaurants.exists():
            raise PermissionDenied("You do not own any restaurant.")
        
        # Optional: Assign the first restaurant if multiple exist
        # You can also accept restaurant_id from request.data and validate ownership
        serializer.save(restaurant=restaurants.first())

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
