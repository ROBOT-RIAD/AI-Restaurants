from django.contrib import admin
from .models import Restaurant,OpenAndCloseTime

# Register your models here.


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('resturent_name', 'address', 'phone_number_1', 'twilio_number', 'opening_time', 'closing_time', 'owner', 'website', 'iban', 'tax_number','image')
    search_fields = ('resturent_name', 'address', 'owner__username')
    list_filter = ('owner',)




@admin.register(OpenAndCloseTime)
class OpenAndCloseTimeAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'day_of_week', 'opening_time', 'closing_time', 'created_at', 'updated_at')
    list_filter = ('day_of_week', 'restaurant')
    search_fields = ('restaurant__name',)

    
