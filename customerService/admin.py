
from django.contrib import admin
from .models import CustomerService

# Register your models here.


@admin.register(CustomerService)
class CustomerServiceAdmin(admin.ModelAdmin):
    list_display = ('get_customer_name', 'get_customer_phone', 'get_customer_email', 'restaurant', 'created_at', 'updated_at')
    search_fields = ('customer__customer_name', 'customer__email', 'customer__phone')
    list_filter = ('restaurant', 'created_at')  
    ordering = ('-created_at',) 
    fields = ('customer', 'restaurant', 'service_summary', 'callback_done', 'type')

    def get_customer_name(self, obj):
        return obj.customer.customer_name if obj.customer else "-"
    get_customer_name.short_description = 'Customer Name'

    def get_customer_phone(self, obj):
        return obj.customer.phone if obj.customer else "-"
    get_customer_phone.short_description = 'Phone'

    def get_customer_email(self, obj):
        return obj.customer.email if obj.customer else "-"
    get_customer_email.short_description = 'Email'
