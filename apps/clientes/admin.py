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
        "lider", "inicio", "fim", "valor_repasse_recebido", "valor_esperado", "valor_pago",
        "valor_pendente_display", "repassar_pendente", "diferenca_display", "pago", "data_pagamento",
    )
    list_filter = ("pago", "lider", "repassar_pendente", DivergenciaFilter)
    fields = (
        "lider", "inicio", "fim", "valor_repasse_recebido", "valor_esperado", "comprovante_pagamento",
        "valor_pago", "valor_pendente_display", "valor_pendente_ajustado", "repassar_pendente",
        "diferenca_display", "diagnostico_diferenca", "observacao_divergencia", "pago", "data_pagamento",
    )

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):
        readonly = [
            "lider", "inicio", "fim", "valor_repasse_recebido", "valor_esperado",
            "valor_pendente_display", "diferenca_display",
        ]
        # Uma vez que o valor pago é informado, ele passa a mandar (ver
        # FechamentoMedicao.save()) - o checkbox/data manuais deixam de ter
        # efeito, então ficam só como exibição pra não confundir.
        if obj is not None and obj.valor_pago is not None:
            readonly += ["pago", "data_pagamento"]
        return readonly

    def diferenca_display(self, obj):
        diferenca = obj.diferenca
        if diferenca is None:
            return "—"
        if diferenca == 0:
            return "Sem diferença"
        sinal = "+" if diferenca > 0 else ""
        return f"{sinal}{diferenca} ⚠ divergente"

    diferenca_display.short_description = "Diferença (pago - esperado)"

    def valor_pendente_display(self, obj):
        pendente = obj.valor_pendente_efetivo
        if pendente is None:
            return "—"
        if pendente == 0:
            return "Nada pendente"
        rotulo = f"R$ {pendente} pendente"
        if obj.valor_pendente_ajustado is not None:
            rotulo += " (ajustado manualmente)"
        elif obj.repassar_pendente:
            rotulo += " - vai pra próxima semana"
        else:
            rotulo += " - repasse desligado"
        return rotulo

    valor_pendente_display.short_description = "Valor pendente"

    def save_model(self, request, obj, form, change):
        # obj.save() (FechamentoMedicao.save) já cobre o caso em que valor_pago
        # foi informado; isso aqui só mantém o toggle manual de "pago" pra
        # fechamentos que ainda não usam o fluxo de comprovante/valor pago.
        if obj.valor_pago is None:
            if obj.pago and not obj.data_pagamento:
                obj.data_pagamento = timezone.now()
            elif not obj.pago:
                obj.data_pagamento = None
        super().save_model(request, obj, form, change)

        # Preenche o diagnóstico automático na primeira vez que aparece uma
        # divergência (sem sobrescrever se o admin já escreveu algo nesse
        # campo); limpa de novo quando a divergência é resolvida (ex.:
        # completou o pagamento), pra não deixar um diagnóstico antigo e
        # desatualizado.
        if obj.tem_divergencia and not obj.diagnostico_diferenca:
            from .views_lider import diagnosticar_diferenca

            diagnostico = diagnosticar_diferenca(obj)
            if diagnostico:
                obj.diagnostico_diferenca = diagnostico
                obj.save(update_fields=["diagnostico_diferenca"])
        elif not obj.tem_divergencia and obj.diagnostico_diferenca:
            obj.diagnostico_diferenca = ""
            obj.save(update_fields=["diagnostico_diferenca"])
