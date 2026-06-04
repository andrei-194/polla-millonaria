from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, InvitationCode


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "is_staff", "date_joined")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "total_points", "total_predictions")


@admin.register(InvitationCode)
class InvitationCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "created_by", "created_at", "is_active", "uses_count", "max_uses", "expires_at")
    list_filter = ("is_active",)
    readonly_fields = ("code", "created_at", "uses_count")
    actions = ["deactivate_codes"]

    @admin.action(description="Desactivar códigos seleccionados")
    def deactivate_codes(self, request, queryset):
        queryset.update(is_active=False)
