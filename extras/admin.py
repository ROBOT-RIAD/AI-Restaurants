from django.contrib import admin
from .models import Extra

# Register your models here.

@admin.register(Extra)
class ExtraAdmin(admin.ModelAdmin):
    list_display = ("id", "restaurant", "extras", "extras_price", "update_at")
    list_filter = ("restaurant",)
    search_fields = ("extras", "restaurant__resturent_name")
