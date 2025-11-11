from django.db import models
from restaurants.models import Restaurant

# Create your models here.

class AreaManagement(models.Model):
    postalcode = models.CharField(max_length=50)
    estimated_delivery_time = models.CharField(max_length=50)  # e.g. "30-45 mins"
    delivery_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='area_managements')

    def __str__(self):
        return f"{self.postalcode}"
