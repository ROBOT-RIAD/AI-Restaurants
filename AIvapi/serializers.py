from rest_framework import serializers
from .models import Assistance,CallInformations



class AssistanceCreateSerializer(serializers.Serializer):
    twilio_number      = serializers.CharField(max_length=20)
    twilio_account_sid = serializers.CharField(max_length=500)
    twilio_auth_token  = serializers.CharField(max_length=500)

    def validate(self, data):
        if Assistance.objects.filter(twilio_number=data["twilio_number"]).exists():
            raise serializers.ValidationError("This Twilio number is already in use.")
        return data



class AssistanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assistance
        fields = ["id","restaurant","twilio_number","vapi_phone_number_id","assistant_id","voice","speed","created_at","updated_at",]



class CallInformationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallInformations
        fields = '__all__'




class CallInformationsCallbackUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallInformations
        fields = ['callback']




class UpdateVoiceIdSerializer(serializers.Serializer):
    speed = serializers.FloatField(required=False, allow_null=True)
    voice_id = serializers.CharField(required=False, default="matilda")

   
    

class UpdateTwilioCredsSerializer(serializers.Serializer):
    twilio_number = serializers.CharField(max_length=20)
    twilio_account_sid = serializers.CharField(max_length=500)
    twilio_auth_token = serializers.CharField(max_length=500)