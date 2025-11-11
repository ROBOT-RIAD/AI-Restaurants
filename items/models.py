from django.db import models
from restaurants.models import Restaurant
from .constants import STATUS_CHOICES
# Create your models here.


class Item(models.Model):
    item_name = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='available')
    descriptions = models.TextField()
    image = models.ImageField(upload_to='media/items/', blank=True, null=True)
    category = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    preparation_time = models.DurationField(help_text="Duration format: hh:mm:ss",blank=True, null=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='items')
    created_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.item_name