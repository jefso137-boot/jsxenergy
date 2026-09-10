from django.contrib import admin
from django.db.models import F
from django.utils import timezone

from .models import Cliente, FechamentoMedicao


class DivergenciaFilter(admin.SimpleListFilter):
    title = "divergência no pagamento"
    parameter_name = "divergencia"

    def lookups(self, request, model_admin):
        return (("sim", "Com divergência"), ("nao", "Sem divergência"))

    def queryset(self, request, queryset):
        if self.value() == "sim":
            return queryset.filter(valor_pago__isnull=False, valor_esperado__isnull=False).exclude(
                valor_pago=F("valor_esperado")
            )
        if self.value() == "nao":
            return queryset.filter(valor_pago=F("valor_esperado"))
        return queryset


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
    list_display = (
        "lider", "inicio", "fim", "valor_esperado", "valor_pago", "diferenca_display", "pago", "data_pagamento",
    )
    list_filter = ("pago", "lider", DivergenciaFilter)
    readonly_fields = ("lider", "inicio", "fim", "valor_esperado", "diferenca_display")
    fields = (
        "lider", "inicio", "fim", "valor_esperado", "valor_pago", "diferenca_display",
        "observacao_divergencia", "pago", "data_pagamento",
    )

    def has_add_permission(self, request):
        return False

    def diferenca_display(self, obj):
        diferenca = obj.diferenca
        if diferenca is None:
            return "—"
        if diferenca == 0:
            return "Sem diferença"
        sinal = "+" if diferenca > 0 else ""
        return f"{sinal}{diferenca} ⚠ divergente"

    diferenca_display.short_description = "Diferença (pago - esperado)"

    def save_model(self, request, obj, form, change):
        if obj.pago and not obj.data_pagamento:
            obj.data_pagamento = timezone.now()
        elif not obj.pago:
            obj.data_pagamento = None
        super().save_model(request, obj, form, change)
