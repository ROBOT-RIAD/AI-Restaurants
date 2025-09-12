from django.db import models
from restaurants.models import Restaurant

# Create your models here.


class CustomerService(models.Model):
    customer_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15,blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    service_summary = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)  

    def __str__(self):
        return self.customer_name
