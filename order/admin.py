from django.contrib import admin
from .models import Order, OrderItem

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'restaurant', 'customer_name', 'email', 'status', 'total_price',
        'phone', 'verified', 'created_at', 'updated_at'
    )
    search_fields = ('customer_name', 'email', 'status', 'restaurant__resturent_name')
    list_filter = ('status', 'restaurant', 'verified', 'created_at')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'delivery_area_json')

    # Group fields into sections
    fieldsets = (
        (None, {
            'fields': ('restaurant', 'customer_name', 'email', 'status', 'total_price', 'verified')
        }),
        ('Contact Information', {
            'fields': ('phone', 'address', 'order_notes', 'allergy')
        }),
        ('Delivery Area', {
            'fields': ('delivery_area', 'delivery_area_json')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )




@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'order', 'item', 'quantity', 'price', 'extras_price', 'get_total_price', 'created_at'
    )
    search_fields = ('order__customer_name', 'item__item_name')
    list_filter = ('order__status', 'item', 'created_at')
    readonly_fields = ('created_at', 'updated_at', 'item_json')

