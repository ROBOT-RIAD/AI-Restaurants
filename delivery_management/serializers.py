from rest_framework import serializers
from .models import AreaManagement



class AreaManagementSerializar(serializers.ModelSerializer):
    class Meta:
        model = AreaManagement
        fields = ['id', 'postalcode', 'estimated_delivery_time', 'delivery_fee', 'restaurant']
        read_only_fields = ['restaurant']
