from django.contrib import admin
from .models import CustomerService

# Register your models here.


@admin.register(CustomerService)
class CustomerServiceAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'phone_number', 'email', 'restaurant', 'created_at', 'updated_at')
    search_fields = ('customer_name', 'email', 'phone_number')
    list_filter = ('restaurant', 'created_at')  
    ordering = ('-created_at',) 
    fields = ('customer_name', 'phone_number', 'email', 'restaurant', 'service_summary')
    def get_restaurant_name(self, obj):
        return obj.restaurant.name
    get_restaurant_name.short_description = 'Restaurant'

