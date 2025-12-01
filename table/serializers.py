from rest_framework import serializers
from .models import Table,Reservation
from datetime import datetime, timedelta, date
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


class TableSerializer(serializers.ModelSerializer):
    table_name = serializers.CharField(required = False)
    status = serializers.CharField(required = False)
    reservation_status = serializers.CharField(required = False)
    total_set = serializers.IntegerField(required = False)

    class Meta:
        model = Table
        fields = ['id', 'restaurant', 'table_name', 'status', 'reservation_status', 'total_set', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at','restaurant','reservation_status']




class TableNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ['table_name']




class ReservationSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.customer_name',required = False)
    address = serializers.CharField(source='customer.address',required = False)
    email = serializers.EmailField(source='customer.email',required = False)
    phone_number = serializers.CharField(source='customer.phone',required = False)

    from_time = serializers.TimeField(format='%H:%M:%S',required = False)
    to_time = serializers.TimeField(format='%H:%M:%S',required = False)
    table_name = TableNameSerializer(source='table', read_only=True)
    guest_no = serializers.IntegerField(required = False)
    date = serializers.DateField(required = False)
    allergy = serializers.CharField(required = False)

    table = serializers.PrimaryKeyRelatedField(queryset=Table.objects.all(), required=False)
    class Meta:
        model = Reservation
        fields = ['id', 'customer', 'customer_name', 'phone_number', 'guest_no','address','allergy', 'status', 'date', 'from_time', 'to_time', 'table', 'email', 'created_at', 'updated_at','table_name']
        read_only_fields = ['created_at', 'updated_at','customer']


    def update(self, instance, validated_data):
        customer_data = validated_data.pop('customer', {})
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if instance.customer and customer_data:
            for attr, value in customer_data.items():
                setattr(instance.customer, attr, value)
            instance.customer.save()

        return instance

