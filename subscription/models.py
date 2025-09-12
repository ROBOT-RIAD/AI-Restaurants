from django.db import models
from .constants import STATUS_CHOICES
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
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        return f"{self.name} ({self.billing_interval})"
