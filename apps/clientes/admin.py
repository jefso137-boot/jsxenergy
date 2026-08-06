from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "telefone", "email", "cidade", "pago", "criado_por", "criado_em")
    search_fields = ("nome", "telefone", "email", "cidade")
    list_filter = ("pago", "cidade", "criado_por")
    readonly_fields = ("criado_por",)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.criado_por = request.user
        super().save_model(request, obj, form, change)
