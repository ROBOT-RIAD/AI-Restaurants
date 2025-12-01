from rest_framework import serializers
from .models import Extra

class ExtraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Extra
        fields = ['id', 'extras', 'extras_price', 'update_at']
        read_only_fields = ['update_at']