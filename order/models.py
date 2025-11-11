from django.db import models
from items.models import Item
from restaurants.models import Restaurant
from .constants import STATUS_CHOICES,ORDER_TYPE_CHOICES
from delivery_management.models import AreaManagement



# Create your models here.
class Order(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='orders')
    customer_name = models.CharField(max_length=255)
    email = models.EmailField(null=True, blank=True)
    status = models.CharField(max_length=50,choices=STATUS_CHOICES)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    phone = models.CharField(max_length=15,null=True, blank=True)
    order_notes = models.TextField(null=True, blank=True)
    discount_text = models.TextField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    allergy = models.TextField(null=True, blank=True)
    delivery_area = models.ForeignKey(AreaManagement, on_delete=models.SET_NULL,null=True,blank=True,related_name='order')
    delivery_area_json = models.JSONField(null=True, blank=True)
    verified = models.BooleanField(default=True,null=True, blank=True)
    order_type = models.CharField(max_length=20,choices=ORDER_TYPE_CHOICES,default='delivery',help_text="Select whether the order is for pickup or delivery",null=True,blank=True)
   
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer_name}"
    





class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    extras = models.TextField(null=True, blank=True)
    extras_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    special_instructions = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    item_json = models.JSONField(null=True, blank=True)

    def get_total_price(self):
        total_price = self.quantity * self.price

        if self.item.discount:
            discount_percentage = self.item.discount
            discount_amount = (discount_percentage / 100) * total_price
            total_price -= discount_amount

        if self.extras_price:
            total_price += self.extras_price

        return total_price

    def __str__(self):
        return f"OrderItem {self.id} - {self.item.item_name}"
    




