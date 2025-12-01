from django.db import models

# Create your models here.


class Customer(models.Model):
    customer_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(unique=True,max_length=20,blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.customer_name