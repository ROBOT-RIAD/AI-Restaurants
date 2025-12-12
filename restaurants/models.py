from django.db import models
from accounts.models import User


# Create your models here.


class Restaurant(models.Model):
    resturent_name = models.CharField(max_length=255)
    address =  models.CharField(max_length=300)
    phone_number_1 = models.CharField(max_length=20, blank=True, null=True) 
    twilio_number = models.CharField(max_length=20, blank=True, null=True ,unique=True)
    opening_time = models.TimeField(blank=True, null=True)
    closing_time = models.TimeField(blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='restaurants')
    image = models.ImageField(upload_to='media/restaurant', blank=True, null=True)

    website = models.URLField(max_length=500, blank=True, null=True)  
    iban = models.CharField(max_length=300, blank=True, null=True)
    tax_number = models.CharField(max_length=300, blank=True, null=True)
    total_vapi_minutes = models.IntegerField(default=0)
    forword_mode = models.CharField(max_length=50,blank=True,null=True,help_text="Specify the restaurant's forwarding mode (e.g., auto, manual, off)")

    def __str__(self):
        return f"{self.resturent_name} - {self.address}"
    




class OpenAndCloseTime(models.Model):
    restaurant = models.ForeignKey(Restaurant,on_delete=models.CASCADE, related_name='open_close_times')
    day_of_week = models.CharField(max_length=10, choices=[
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ])
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    is_closed = models.BooleanField(default=False,blank=True,null=True, help_text="Mark true if the restaurant is closed on this day")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)



    