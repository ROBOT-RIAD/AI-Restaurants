from django.contrib import admin
from .models import Package
# Register your models here.

@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'amount', 'billing_interval', 'interval_count', 'status']
    readonly_fields = ['product_id', 'price_id']

