from rest_framework import serializers
from .models import User
from restaurants.models import Restaurant
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import update_last_login
from rest_framework.exceptions import APIException
from subscription.models import Subscription


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['approved','extrapassword','username','email','password']

        def create(self, validated_data):
            email = validated_data['email']
            username = email
            user = User.objects.create_user(username=username,**validated_data)
            admin_profile = User.objects.filter(role="admin", adminapproved=True).first()
            if admin_profile:
                user.approved = True
            else:
                user.approved = False
            user.save()
            return user





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
        fields = ['id','resturent_name', 'address', 'phone_number_1', 'twilio_number', 'opening_time', 'closing_time', 'owner','website', 'iban', 'tax_number','image','total_vapi_minutes']
        read_only_fields = ['total_vapi_minutes']

    def create(self, validated_data):
        user = validated_data.pop('owner')
        restaurant = Restaurant.objects.create(owner=user, **validated_data)
        return restaurant
    




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

        # user = User.objects.get(email=validated_data['email'])

        try:
            user = User.objects.get(email=validated_data['email'])
            raise APIException(detail="user already exists")
        except User.DoesNotExist:
            user = User.objects.create_user(**user_data)

        admin_profile = User.objects.filter(role="admin", adminapproved=True).first()
        if admin_profile:
            user.approved = True
        else:
            user.approved = False
        user.save()

        # Create restaurant and link to the user
        restaurant_data['owner'] = user.pk
        restaurant_serializer = RestaurantSerializer(data=restaurant_data)
        if 'image' in validated_data:
            restaurant_data['image'] = validated_data['image']
        restaurant_serializer.is_valid(raise_exception=True)
        restaurant = restaurant_serializer.save()
        return user, restaurant
    




class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password']

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password")

        data = super().validate({'email': user.email, 'password': password})
        
        update_last_login(None, user)
        # Check if the user has an associated restaurant
        restaurant = Restaurant.objects.filter(owner=user).first()
        if restaurant:
            # If restaurant exists, add it to the response
            data['restaurant'] = {
                'id': restaurant.id,
                'resturent_name': restaurant.resturent_name,
                'address': restaurant.address,
                'phone_number_1': restaurant.phone_number_1,
                'twilio_number': restaurant.twilio_number,
                'opening_time': restaurant.opening_time,
                'closing_time': restaurant.closing_time,
                'website': restaurant.website,
                'iban': restaurant.iban,
                'tax_number': restaurant.tax_number,
                'total_vapi_minutes' : restaurant.total_vapi_minutes
            }
        else:
            # No restaurant found, optionally add this information
            data['restaurant'] = None  # Or skip this line if you don't want to include restaurant data at all

        
        subscription = Subscription.objects.filter(
            user=user,
            is_active=True
        ).order_by('-created_at').first()

        if subscription:
            data['subscription'] = {
                "package_name": subscription.package_name,
                "price": subscription.price,
                "price_id": subscription.price_id,
                "billing_interval_count": subscription.billing_interval_count,
                "status": subscription.status,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "start_date": subscription.start_date,
                "current_period_end": subscription.current_period_end,
                "end_date": subscription.end_date,
                "is_active": subscription.is_active
            }
        else:
            data['subscription'] = None

        data['user'] = {
            'id': user.id,
            'email': user.email,
            'role': user.role,
            'approved': user.approved
        }

        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['id'] = user.id
        token['email'] = user.email
        token['role'] = user.role

        # Check if the user has a restaurant
        restaurant = Restaurant.objects.filter(owner=user).first()
        if restaurant:
            token['restaurant_id'] = restaurant.id
        else:
            token['restaurant_id'] = None  # Add this line to handle the case where there's no restaurant

        return token




class SendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist.")
        return value
    




class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=4)




class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=4)
    confirm_password = serializers.CharField(write_only=True, min_length=4)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs
    



class RestaurantFullDataserializer(serializers.ModelSerializer):
    twilio_number = serializers.CharField(max_length=20)

