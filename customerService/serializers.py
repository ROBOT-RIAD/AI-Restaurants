from rest_framework import serializers
from .models import CustomerService

class CustomerServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerService
        fields = ['customer_name', 'phone_number', 'email', 'restaurant', 'service_summary','created_at' ,'updated_at']
        read_only_fields = ['created_at' ,'updated_at']