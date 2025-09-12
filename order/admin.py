from django.contrib import admin
from .models import Order, OrderItem

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'restaurant', 'customer_name', 'email', 'status', 'total_price', 'phone', 
        'order_notes', 'address', 'created_at', 'updated_at'
    )
    search_fields = ('customer_name', 'email', 'status', 'restaurant__name')
    list_filter = ('status', 'restaurant', 'created_at')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    # Group fields into sections (with fieldsets)
    fieldsets = (
        (None, {
            'fields': ('restaurant', 'customer_name', 'email', 'status', 'total_price')
        }),
        ('Contact Information', {
            'fields': ('phone', 'address', 'order_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)  # Optional: collapse the timestamps section
        }),
    )




@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'item', 'quantity', 'price', 'extras_price', 'get_total_price', 'created_at')
    search_fields = ('order__customer_name', 'item__item_name')
    list_filter = ('order__status', 'item', 'created_at')
    readonly_fields = ('created_at', 'updated_at')

