from django.contrib import admin
from .models import Assistance,CallInformations

# Register your models here.



@admin.register(Assistance)
class AssistanceAdmin(admin.ModelAdmin):
    list_display = (
        'restaurant_name',
        'twilio_number',
        'vapi_phone_number_id',
        'assistant_id',
        'created_at',
        'updated_at',
    )
    search_fields = (
        'restaurant__resturent_name',
        'twilio_number',
        'vapi_phone_number_id',
        'assistant_id',
    )
    list_filter = ('created_at', 'updated_at')

    def restaurant_name(self, obj):
        return obj.restaurant.resturent_name
    restaurant_name.short_description = 'Restaurant'





@admin.register(CallInformations)
class CallInformationsAdmin(admin.ModelAdmin):
    list_display = (
        "type",
        "call_date_utc",
        "duration_seconds",
        "phone",
        "assistant_id",
        "customer_name",
    )
    search_fields = ("phone", "customer_name", "assistant_id")
    list_filter = ("type", "call_date_utc")