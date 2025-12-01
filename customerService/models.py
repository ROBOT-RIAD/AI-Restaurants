   
from django.db import models
from restaurants.models import Restaurant
from .constants import TYPE_CHOICES
from customer.models import Customer

# Create your models here.


class CustomerService(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, related_name='services', null=True,blank=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.SET_NULL, null=True,blank=True)
    service_summary = models.TextField(blank=True, null=True)
    callback_done = models.BooleanField(default=False)
    type = models.CharField(max_length=10,choices=TYPE_CHOICES,default='service')
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)  

    def __str__(self):
        return self.customer.customer_name if self.customer else self.service_summary or f"Service #{self.id}"

