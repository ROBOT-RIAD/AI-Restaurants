from django.db import models
from django.core.exceptions import ValidationError
from restaurants.models import Restaurant
from .constants import CALL_TYPE_CHOICES
from datetime import datetime
from .utils import encrypt_text, decrypt_text



class Assistance(models.Model):
    restaurant = models.OneToOneField(Restaurant, on_delete=models.CASCADE, related_name='ai_assistance')
    twilio_number = models.CharField(max_length=20, unique=True)
    twilio_account_sid_encrypted = models.CharField(max_length=500)
    twilio_auth_token_encrypted = models.CharField(max_length=500)


    vapi_phone_number_id = models.CharField(max_length=500, unique=True)  
    assistant_id = models.CharField(max_length=500, unique=True)
    voice = models.CharField(max_length=100,default="matilda",blank=True,null=True,help_text="Voice ID or name for the AI assistant.")   
    speed = models.DecimalField(max_digits=4,default=1.0,decimal_places=1,blank=True,null=True,help_text="Speech speed multiplier (e.g. 0.7 = slower, 1.2 = faster).")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def twilio_account_sid(self):
        return decrypt_text(self.twilio_account_sid_encrypted)

    @twilio_account_sid.setter
    def twilio_account_sid(self, value):
        self.twilio_account_sid_encrypted = encrypt_text(value)

    @property
    def twilio_auth_token(self):
        return decrypt_text(self.twilio_auth_token_encrypted)

    @twilio_auth_token.setter
    def twilio_auth_token(self, value):
        self.twilio_auth_token_encrypted = encrypt_text(value)

    def __str__(self):
        return f"AI Assistance for {self.restaurant.resturent_name}"

    def __str__(self):
        return f"AI Assistance for {self.restaurant.resturent_name}"
    




class CallInformations(models.Model):
    type = models.CharField(max_length=100,choices=CALL_TYPE_CHOICES,blank=True , null = True)
    call_date_utc = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.CharField(max_length=100)
    summary = models.TextField()
    recording = models.CharField(max_length=1000)
    phone = models.CharField(max_length=15,null=True, blank=True)
    assistant_id = models.CharField(max_length=500,null=True, blank=True)
    customer_name = models.CharField(max_length=255,null=True, blank=True)
    callback = models.BooleanField(default=False)
    callback_track = models.BooleanField(default=False,null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    






