from rest_framework import serializers
from .models import CustomerService
from customer.models import Customer

class CustomerServiceSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    address = serializers.CharField(required=False)

    class Meta:
        model = CustomerService
        fields = [
            'customer', 'customer_name', 'phone', 'email', 'address',
            'restaurant', 'service_summary', 'type', 'callback_done', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'customer']

    def create(self, validated_data):
        customer_name = validated_data.pop('customer_name', None)
        email = validated_data.pop('email', None)
        phone = validated_data.pop('phone', None)
        address = validated_data.pop('address', None)

        print("phone number",phone)

        customer = None
        if phone:
            customer, created = Customer.objects.get_or_create(phone=phone)
            if customer_name:
                customer.customer_name = customer_name
            if email:
                customer.email = email
            if address:
                customer.address = address
            customer.save()

        customer_service = CustomerService.objects.create(customer=customer, **validated_data)
        return customer_service

