from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("Papel JSX Energy", {"fields": ("role", "nome_empresa_recibo")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Papel JSX Energy", {"fields": ("role", "nome_empresa_recibo")}),
    )
