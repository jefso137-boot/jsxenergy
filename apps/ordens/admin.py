from django.contrib import admin

from .models import OrdemServico, OsChecklistResposta, OsFoto


class OsFotoInline(admin.TabularInline):
    model = OsFoto
    extra = 0
    fields = ("ordem", "titulo_secao", "imagem", "legenda")


class OsChecklistRespostaInline(admin.TabularInline):
    model = OsChecklistResposta
    extra = 0
    fields = ("item", "marcado", "texto", "foto", "observacao")
    autocomplete_fields = ["item"]


@admin.register(OrdemServico)
class OrdemServicoAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "tipo", "tecnico", "status", "data_agendada", "data_conclusao")
    list_filter = ("status", "tipo", "tecnico")
    search_fields = ("cliente__nome",)
    date_hierarchy = "data_agendada"
    readonly_fields = ("data_conclusao", "pdf_file")
    inlines = [OsChecklistRespostaInline, OsFotoInline]
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
        ("Conclusão", {"fields": ("data_conclusao", "pdf_file")}),
    )
