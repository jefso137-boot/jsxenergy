from django.contrib import admin
from django.utils import timezone

from .models import Cliente, FechamentoMedicao


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


@admin.register(FechamentoMedicao)
class FechamentoMedicaoAdmin(admin.ModelAdmin):
    list_display = ("lider", "inicio", "fim", "pago", "data_pagamento")
    list_filter = ("pago", "lider")
    readonly_fields = ("lider", "inicio", "fim")

    def has_add_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        if obj.pago and not obj.data_pagamento:
            obj.data_pagamento = timezone.now()
        elif not obj.pago:
            obj.data_pagamento = None
        super().save_model(request, obj, form, change)
