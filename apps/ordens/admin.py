from django.contrib import admin

from .models import OrdemServico, OsChecklistResposta


class OsChecklistRespostaInline(admin.TabularInline):
    """Somente leitura: mostra o que o técnico já respondeu. O checklist certo
    para o tipo da OS é puxado automaticamente na tela do técnico, sem precisar
    escolher itens manualmente aqui."""

    model = OsChecklistResposta
    extra = 0
    fields = ("item", "marcado", "texto", "foto", "observacao")
    can_delete = False
    verbose_name_plural = "Respostas do checklist preenchidas pelo técnico"

    def has_add_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return self.fields


@admin.register(OrdemServico)
class OrdemServicoAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "tipo", "tecnico", "status", "criado_por", "data_agendada", "data_conclusao")
    list_filter = ("status", "tipo", "tecnico", "criado_por")
    search_fields = ("cliente__nome",)
    date_hierarchy = "data_agendada"
    readonly_fields = ("criado_por", "data_conclusao", "pdf_file")
    fieldsets = (
        (None, {"fields": ("cliente", "tipo", "tecnico", "status", "data_agendada", "observacoes")}),
        (
            "Conteúdo do relatório (PDF)",
            {
                "fields": (
                    "status_pill_text",
                    "cover_footnote",
                    "narrativa_paragrafos",
                    "resumo_tecnico_bullets",
                )
            },
        ),
        ("Conclusão", {"fields": ("criado_por", "data_conclusao", "pdf_file")}),
    )

    def get_inlines(self, request, obj):
        if obj is None:
            return []
        return [OsChecklistRespostaInline]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.criado_por = request.user
        super().save_model(request, obj, form, change)
