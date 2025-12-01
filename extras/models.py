from django.db import models
from restaurants.models import Restaurant

# Create your models here.


class Extra(models.Model):
    restaurant = models.ForeignKey(Restaurant,on_delete=models.CASCADE,related_name='extras')
    extras = models.CharField(max_length=200)
    extras_price = models.DecimalField(max_digits=6, decimal_places=2)
    update_at = models.DateTimeField(auto_now=True)
