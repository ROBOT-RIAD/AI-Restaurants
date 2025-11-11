from rest_framework import serializers
from .models import OpenAndCloseTime


class OpenAndCloseTimeSealizer(serializers.ModelSerializer):
    restaurant = serializers.PrimaryKeyRelatedField(read_only=True, required=False)
    day_of_week = serializers.CharField(required=False, allow_blank=True)
    opening_time = serializers.TimeField(required=False, allow_null=True)
    closing_time = serializers.TimeField(required=False, allow_null=True)
    is_closed = serializers.BooleanField(required=False, default=False)
    class Meta:
        model = OpenAndCloseTime
        fields = ['id', 'restaurant', 'day_of_week', 'opening_time', 'closing_time','is_closed', 'created_at', 'updated_at']
        read_only_fields = ['id', 'restaurant', 'created_at', 'updated_at']


