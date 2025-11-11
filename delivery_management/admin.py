from django.contrib import admin
from .models import AreaManagement

# Register your models here.

@admin.register(AreaManagement)
class AreaManagementAdmin(admin.ModelAdmin):
    list_display = ('id', 'postalcode', 'estimated_delivery_time', 'delivery_fee', 'restaurant')
    search_fields = ('postalcode', 'restaurant__name')
    list_filter = ('restaurant',)