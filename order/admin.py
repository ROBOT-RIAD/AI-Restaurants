from django.contrib import admin
from .models import Order, OrderItem

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'restaurant', 'get_customer_name', 'get_email', 'status', 'total_price',
        'get_phone', 'verified', 'created_at', 'updated_at'
    )

    readonly_fields = (
        'created_at', 'updated_at', 'delivery_area_json',
        'get_customer_name', 'get_email', 'get_phone', 'get_address'
    )

    fieldsets = (
        (None, {
            'fields': ('restaurant', 'status', 'total_price', 'verified')
        }),
        ('Customer Information', {
            'fields': (
                'get_customer_name',
                'get_email',
                'get_phone',
                'get_address',
            )
        }),
        ('Delivery Area', {
            'fields': ('delivery_area', 'delivery_area_json')
        }),
        ('Timestamps', {
            'fields': (),
            'classes': ('collapse',)
        }),
    )

    # Methods to display customer info
    def get_customer_name(self, obj):
        return obj.customer.customer_name if obj.customer else "-"
    get_customer_name.short_description = "Customer Name"

    def get_email(self, obj):
        return obj.customer.email if obj.customer else "-"
    get_email.short_description = "Email"

    def get_phone(self, obj):
        return obj.customer.phone if obj.customer else "-"
    get_phone.short_description = "Phone"

    def get_address(self, obj):
        return obj.customer.address if obj.customer else "-"
    get_address.short_description = "Address"




@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'order', 'item', 'quantity', 'price', 'extras_price', 'get_total_price', 'created_at'
    )
    search_fields = ('order__customer_name', 'item__item_name')
    list_filter = ('order__status', 'item', 'created_at')
    readonly_fields = ('created_at', 'updated_at', 'item_json')

