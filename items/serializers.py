from rest_framework import serializers
from .models import Item


class ExtendedFileField(serializers.FileField):
    def to_representation(self, value):
        if value:
            request = self.context.get('request')
            url = getattr(value, 'url', value)
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        return None




class ItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    descriptions = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    image = ExtendedFileField(required=False,allow_null=True)
    category = serializers.CharField(required=False)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False,allow_null=True)
    discount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False,allow_null=True)
    preparation_time = serializers.DurationField(required=False,allow_null=True)
    
    class Meta:
        model = Item
        fields = ['id','item_name','status','descriptions','image','category','price','discount','preparation_time','restaurant','created_time','updated_time']
        read_only_fields = ['created_time', 'updated_time','restaurant']  
    
    def to_internal_value(self, data):
        if not data.get('image'):
            data['image'] = None 
        return super().to_internal_value(data)
    


class MenuFileSerializer(serializers.Serializer):
    files = serializers.ListField(child=serializers.FileField(allow_empty_file=False),required=True)
