from rest_framework import serializers
from accounts.models import User
from restaurants.models import Restaurant
from subscription.models import Subscription
from AIvapi.models import CallInformations
from table.models import Reservation
from order.models import Order
from rest_framework.exceptions import APIException
from AIvapi.models import Assistance



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
        
        try:
            user = User.objects.get(email=validated_data['email'])
            raise APIException(detail="user already exists")
        except User.DoesNotExist:
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
    



class RestaurantSerializerList(serializers.ModelSerializer):
    image = ExtendedFileField(required=False)
    subscriptions = serializers.SerializerMethodField()
    total_calls = serializers.SerializerMethodField()
    total_orders = serializers.SerializerMethodField()
    total_reservations = serializers.SerializerMethodField()
    owner_extrapassword = serializers.SerializerMethodField()
    subscriptions = serializers.SerializerMethodField()
    assistance = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = [
            "id","image", "resturent_name", "address", "phone_number_1", "twilio_number",
            "opening_time", "closing_time", "owner", "website", "iban", "tax_number",
            "subscriptions","assistance", "total_calls", "total_orders", "total_reservations","owner_extrapassword"
        ]

    def get_subscriptions(self, obj):
        subs = Subscription.objects.filter(user=obj.owner, is_active=True).first()
        if subs:
            return {
                "package_name": subs.package_name,
                "price": str(subs.price),
                "status": subs.status,
                "start_date": subs.start_date,
                "end_date": subs.end_date,
            }
        return {}
    
    def get_assistance(self, obj):
        """Return the assistant info for this restaurant using a filter query."""
        assistance = Assistance.objects.filter(restaurant=obj).first()
        if assistance:
            return {
                "assistant_id": assistance.assistant_id,
                "twilio_number": assistance.twilio_number,
                "voice": assistance.voice,
                "speed": float(assistance.speed) if assistance.speed else 1.0,
                "created_at": assistance.created_at,
                "updated_at": assistance.updated_at,
            }
        return {}

    def get_total_calls(self, obj):
        return CallInformations.objects.filter(assistant_id=obj.ai_assistance.assistant_id if hasattr(obj, 'ai_assistance') else None).count()

    def get_total_orders(self, obj):
        return obj.orders.count()

    def get_total_reservations(self, obj):
        return Reservation.objects.filter(table__restaurant=obj).count()
    

    def get_owner_extrapassword(self, obj):
        try:
            return obj.owner.get_decrypted_extrapassword()
        except Exception:
            return None
    




class RestaurantSerializerStatus(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    owner_last_login = serializers.DateTimeField(source='owner.last_login', read_only=True)
    owner_approved = serializers.BooleanField(source='owner.approved', read_only=True)
    owner_id = serializers.IntegerField(source='owner.id', read_only=True)

    class Meta:
        model = Restaurant
        fields = [
            'id',
            'resturent_name',
            'address',
            'phone_number_1',
            'twilio_number',
            'opening_time',
            'closing_time',
            'image',
            'website',
            'iban',
            'tax_number',
            'total_vapi_minutes',
            'owner_email',
            'owner_last_login',
            'owner_approved',
            'owner_id',
        ]



class UserApprovalUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['approved']
    



class RestaurantOrderSummarySerializer(serializers.Serializer):
    resturent_name = serializers.CharField()
    image = serializers.SerializerMethodField()
    resturant_total_revinew = serializers.DecimalField(max_digits=12, decimal_places=2)

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url)
        return None

    



class CallSummarySerializer(serializers.Serializer):
    total_call = serializers.IntegerField()
    total_minute_use = serializers.FloatField()
    total_order = serializers.IntegerField()
    total_reservations = serializers.IntegerField()
    order = RestaurantOrderSummarySerializer(many=True)




class TopSellingItemSerializer(serializers.Serializer):
    item_name = serializers.CharField()
    total_sells = serializers.IntegerField()



class RestaurantCallStatsSerializer(serializers.Serializer):
    resturent_name = serializers.CharField()
    image = ExtendedFileField(required= False)
    total_used_minute = serializers.FloatField()
    total_cost = serializers.DecimalField(max_digits=14, decimal_places=2)





class AdminApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['adminapproved']