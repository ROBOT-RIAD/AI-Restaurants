from django.contrib import admin
from .models import Customer
# Register your models here.

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "email", "phone", "address", "created_at")
    search_fields = ("customer_name", "email", "phone")
    list_filter = ("created_at",)
    ordering = ("-created_at",)
