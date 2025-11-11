from django.contrib import admin
from .models import Table,Reservation

# Register your models here.

@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('table_name', 'restaurant', 'status', 'reservation_status', 'total_set', 'created_at', 'updated_at')
    list_filter = ('status', 'reservation_status', 'restaurant')
    search_fields = ('table_name', 'restaurant__resturent_name')
    ordering = ('restaurant', 'table_name')





@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'phone_number','verified', 'guest_no', 'status', 'date', 'from_time', 'to_time', 'table', 'email', 'created_at', 'updated_at']
    search_fields = ['customer_name', 'phone_number', 'status', 'email']
    list_filter = ['status', 'date', 'table']
    
    fieldsets = (
        (None, {
            'fields': ('customer_name', 'phone_number', 'guest_no', 'status', 'date', 'from_time', 'to_time', 'table', 'email')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-date', '-from_time']
    date_hierarchy = 'date'

