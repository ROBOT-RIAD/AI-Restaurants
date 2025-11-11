from rest_framework import serializers
from restaurants.models import Restaurant
from accounts.models import User



class ExtendedFileField(serializers.FileField):
    def to_representation(self, value):
        if value:
            request = self.context.get('request')
            url = getattr(value, 'url', value)
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        return None




class RestaurantSerializerInfo(serializers.ModelSerializer):
    resturent_name = serializers.CharField(max_length=255,required=False)
    address = serializers.CharField(max_length=300,required=False)
    phone_number_1 = serializers.CharField(max_length=20, required=False)
    website = serializers.URLField(max_length=500, required=False)
    iban = serializers.CharField(max_length=300, required=False)
    tax_number = serializers.CharField(max_length=300, required=False)
    image = ExtendedFileField(required=False)
    forword_mode = serializers.CharField(max_length=50, required=False)
    
    class Meta:
        model = Restaurant
        fields = ['id','resturent_name', 'address', 'phone_number_1', 'twilio_number', 'opening_time', 'closing_time', 'owner', 'website', 'iban', 'tax_number', 'image','total_vapi_minutes','forword_mode']
        read_only_fields = ['owner','twilio_number','total_vapi_minutes']




class UserRestaurantSerializerInfo(serializers.ModelSerializer):
    restaurant = RestaurantSerializerInfo(source='restaurants.first', read_only=True)

    class Meta:
        model = User
        fields = ['email', 'role', 'approved','restaurant']  

    def create(self, validated_data):
        user_data = validated_data
        user = User.objects.create_user(**user_data)
        return user




class RestaurantStatsSerializer(serializers.Serializer):
    total_revenue_order = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_calls = serializers.IntegerField()
    total_number_of_orders = serializers.IntegerField()
    total_number_of_reservations = serializers.IntegerField()
    number_of_new_customers = serializers.IntegerField()
    number_of_return_customers = serializers.IntegerField()
    total_duration_seconds = serializers.IntegerField() 
    total_callback_track = serializers.IntegerField()



    