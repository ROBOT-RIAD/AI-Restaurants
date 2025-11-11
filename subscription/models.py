from django.db import models
from .constants import STATUS_CHOICES
from accounts.models import User
# Create your models here.



class Package(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='media/package_images/', blank=True, null=True)
    recurring = models.BooleanField(default=True)
    amount = models.FloatField(help_text="In dollars (e.g., 9.99)")
    billing_interval = models.CharField(max_length=20, help_text="e.g., day, month, year")
    interval_count = models.IntegerField(default=1, help_text="Number of intervals (e.g., every 6 months = 6)")
    price_id = models.CharField(max_length=255, blank=True, null=True)
    product_id = models.CharField(max_length=255, blank=True, null=True)
    vapi_minutes = models.IntegerField(default=0,blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        return f"{self.name} ({self.billing_interval})"
    




class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    stripe_customer_id = models.CharField(max_length=255)
    stripe_subscription_id = models.CharField(max_length=255)
    price_id = models.CharField(max_length=100, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    package_name = models.CharField(max_length=100, null=True, blank=True)
    billing_interval_count = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    start_date = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    latest_invoice = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        
        return f"{self.user.email} - {self.package_name}"
    
    def is_active_subscription(self):
        return self.is_active





class StripeEventLog(models.Model):
    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.event_id