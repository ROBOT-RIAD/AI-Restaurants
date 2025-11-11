from django.contrib import admin
from .models import Item

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    # Define the fields to be displayed in the list view
    list_display = (
        'item_name',
        'status',
        'category',
        'price',
        'discount',
        'preparation_time',
        'restaurant',
        'created_time',
        'updated_time',
    )
    search_fields = ('item_name', 'category', 'restaurant__resturent_name')
    list_filter = ('status', 'category', 'restaurant')
    ordering = ('-created_time',)
    fields = (
        'item_name',
        'status',
        'descriptions',
        'image',
        'category',
        'price',
        'discount',
        'preparation_time',
        'restaurant',
    )

    readonly_fields = ('created_time', 'updated_time')
