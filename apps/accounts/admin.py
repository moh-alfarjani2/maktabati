from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Role, CustomUser, ActivityLog

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_name_display', 'description')
    
    def get_name_display(self, obj):
        return obj.get_name_display()
    get_name_display.short_description = 'اسم الدور'

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'full_name', 'role', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('full_name', 'role', 'phone')}),
    )

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'action_description', 'timestamp')
    list_filter = ('user', 'action', 'timestamp')
    readonly_fields = ('user', 'action', 'action_description', 'timestamp', 'object_type', 'object_id', 'old_value', 'new_value', 'ip_address')
    search_fields = ('action_description', 'object_id')
