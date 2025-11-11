from django.contrib import admin
from .models import Support

# Register your models here.



class SupportAdmin(admin.ModelAdmin):
    list_display = ('issue', 'restaurant', 'created_at', 'updated_at', 'uploaded_file')
    search_fields = ('issue', 'restaurant__name')
    list_filter = ('restaurant', 'created_at')
    fieldsets = (
        (None, {
            'fields': ('restaurant', 'issue', 'issue_details', 'uploaded_file')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    def has_change_permission(self, request, obj=None):
        return True 

admin.site.register(Support, SupportAdmin)
