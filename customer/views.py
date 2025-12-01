from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

from .models import Customer
from .serializers import CustomerSerializer
from accounts.permissions import IsOwnerRole

#swagger
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class CustomerViewSet(ModelViewSet):
    queryset = Customer.objects.all().order_by('-id')
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated, IsOwnerRole]
    pagination_class = None

    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["phone", "customer_name"]
    search_fields = ["customer_name", "phone"]

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
