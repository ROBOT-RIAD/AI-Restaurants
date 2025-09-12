from django.contrib import admin
from .models import User , PasswordResetOTP
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

  
@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'approved', 'adminapproved', 'is_staff', 'get_decrypted_extrapassword']
    
    # Add fields to the form when adding/editing users
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('role', 'approved', 'adminapproved', 'extrapassword')}),
    )
    
    # Add these fields to the add user form
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Extra Info', {'fields': ('role', 'approved', 'adminapproved', 'extrapassword')}),
    )

    # Method to decrypt and display the extrapassword field in the admin list
    def get_decrypted_extrapassword(self, obj):
        return obj.get_decrypted_extrapassword() if obj.extrapassword else "Not Set"
    get_decrypted_extrapassword.short_description = 'Decrypted Extra Password'



@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp', 'created_at', 'is_verified')
    search_fields = ('user__email', 'otp')
    list_filter = ('is_verified',)
    ordering = ('created_at',)