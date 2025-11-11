from rest_framework import serializers
from .models import Support

class SupportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Support
        fields = ['restaurant', 'issue', 'issue_details', 'uploaded_file', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'restaurant']



class SupportSerializerGet(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source='restaurant.resturent_name', read_only=True)
    owner_email = serializers.EmailField(source='restaurant.owner.email', read_only=True)
    restaurant_image = serializers.SerializerMethodField()

    class Meta:
        model = Support
        fields = [
            'id',
            'issue',
            'issue_details',
            'uploaded_file',
            'status',
            'created_at',
            'updated_at',
            'restaurant',       
            'restaurant_name',   
            'owner_email',
            'restaurant_image',
        ]

    def get_restaurant_image(self, obj):
        request = self.context.get('request')
        image = obj.restaurant.image
        if image and hasattr(image, 'url'):
            return request.build_absolute_uri(image.url)
        return None




class SupportStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Support
        fields = ['status']




