from django.db import models
from restaurants.models import Restaurant
from .constants import STATUS_CHOICES , RESERVATION_STATUS_CHOICES,RESERVATION_STATUS
from datetime import datetime, timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
# Create your models here.




class Table(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='tables')
    table_name = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    reservation_status = models.CharField(max_length=20, choices=RESERVATION_STATUS_CHOICES, default='available')
    total_set = models.IntegerField(help_text="Total number of seats available at this table.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Table {self.table_name} at {self.restaurant.resturent_name}"
    





class Reservation(models.Model):
    customer_name = models.CharField(max_length=255, help_text="Name of the customer")
    phone_number = models.CharField(blank=True, null=True,max_length=15, help_text="Customer's phone number")
    guest_no = models.IntegerField(help_text="Number of guests in the reservation")
    status = models.CharField(max_length=20, choices=RESERVATION_STATUS, default='reserved', help_text="Reservation status")
    date = models.DateField(help_text="Reservation date")
    from_time = models.TimeField(help_text="Reservation start time (hh:mm:ss format)")
    to_time = models.TimeField(help_text="Reservation end time (hh:mm:ss format)")
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='reservations', help_text="Table reserved")
    email = models.EmailField(blank=True, null=True, help_text="Customer's email address (optional)")
    address = models.TextField(null=True, blank=True)
    allergy = models.TextField(null=True, blank=True)
    verified = models.BooleanField(default=True,null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Reservation for {self.customer_name} on {self.date} from {self.from_time} to {self.to_time}"
    
    




