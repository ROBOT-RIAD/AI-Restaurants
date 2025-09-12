from rest_framework import serializers
from accounts.models import User
from restaurants.models import Restaurant



class ExtendedFileField(serializers.FileField):
    def to_representation(self, value):
        if value:
            request = self.context.get('request')
            url = getattr(value, 'url', value)
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        return None




class RestaurantSerializer(serializers.ModelSerializer):
    image = ExtendedFileField(required=False)
    class Meta:
        model = Restaurant
        fields = ["image",'resturent_name', 'address', 'phone_number_1', 'twilio_number', 'opening_time', 'closing_time', 'owner','website', 'iban', 'tax_number']




class UserSerializer(serializers.ModelSerializer):
    restaurant_info = RestaurantSerializer(read_only=True)  # Add restaurant info here

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'role', 'approved', 'adminapproved', 'restaurant_info', 'extrapassword']




class UserRestaurantSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    # Restaurant Fields
    resturent_name = serializers.CharField(max_length=255)
    address = serializers.CharField(max_length=300)
    phone_number_1 = serializers.CharField(max_length=20, required=False)
    website = serializers.URLField(max_length=500, required=False)
    iban = serializers.CharField(max_length=300, required=False)
    tax_number = serializers.CharField(max_length=300, required=False)
    image = ExtendedFileField(required=False)

    def create(self, validated_data):
        # Extract user and restaurant data
        user_data = {
            'email': validated_data['email'],
            'username': validated_data['email'],
            'password': validated_data['password'],
            'extrapassword': validated_data['password'],
        }

        restaurant_data = {
            'resturent_name': validated_data['resturent_name'],
            'address': validated_data['address'],
            'phone_number_1': validated_data.get('phone_number_1'),
            'website': validated_data.get('website'),
            'iban': validated_data.get('iban'),
            'tax_number': validated_data.get('tax_number'),          
        }
        
        user = User.objects.create_user(**user_data)
        user.approved = True
        user.save()

        restaurant_data['owner'] = user.pk
        restaurant_serializer = RestaurantSerializer(data=restaurant_data)
        if 'image' in validated_data:
            restaurant_data['image'] = validated_data['image']
        restaurant_serializer.is_valid(raise_exception=True)
        restaurant = restaurant_serializer.save()
        return user, restaurant
    

