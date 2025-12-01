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
    list_display = ['get_customer_name','get_phone_number','verified','guest_no','status','date','from_time','to_time','table','get_email','created_at','updated_at',]
    search_fields = ['customer__customer_name','customer__phone','customer__email','status']
    list_filter = ['status', 'date', 'table']
    fieldsets = (
        (None, {
            'fields': (
                'customer',
                'guest_no',
                'status',
                'date',
                'from_time',
                'to_time',
                'table',
                'allergy',
                'verified'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-date', '-from_time']
    date_hierarchy = 'date'

    def get_customer_name(self, obj):
        return obj.customer.customer_name if obj.customer else "-"
    get_customer_name.short_description = "Customer Name"

    def get_phone_number(self, obj):
        return obj.customer.phone if obj.customer else "-"
    get_phone_number.short_description = "Phone"

    def get_email(self, obj):
        return obj.customer.email if obj.customer else "-"
    get_email.short_description = "Email"


