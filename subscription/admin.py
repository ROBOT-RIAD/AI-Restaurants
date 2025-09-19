from django.contrib import admin
from .models import Package,Subscription,StripeEventLog
# Register your models here.

@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'amount', 'billing_interval', 'interval_count', 'status']
    readonly_fields = ['product_id', 'price_id']



@admin.register(StripeEventLog)
class StripeEventLogAdmin(admin.ModelAdmin):
    list_display = ('event_id', 'event_type', 'received_at')
    search_fields = ('event_id', 'event_type')
    list_filter = ('event_type', 'received_at')
    ordering = ('-received_at',)




@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'package_name',
        'status',
        'is_active',
        'start_date',
        'current_period_end',
        'cancel_at_period_end',
        'created_at',
        'billing_interval_count',
    )
    list_filter = ('status', 'is_active', 'cancel_at_period_end', 'created_at')
    search_fields = ('user__email', 'package_name', 'stripe_customer_id', 'stripe_subscription_id')
    ordering = ('-created_at',)



