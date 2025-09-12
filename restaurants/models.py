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

    def __str__(self):
        return f"{self.resturent_name} - {self.address}"


