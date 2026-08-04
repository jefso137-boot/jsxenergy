from django.contrib import admin

from .models import ChecklistItem, ChecklistTemplate


class ChecklistItemInline(admin.TabularInline):
    model = ChecklistItem
    extra = 1
    fields = ("ordem", "descricao", "tipo_campo", "obrigatorio")
    verbose_name = "Pergunta do checklist"
    verbose_name_plural = "Perguntas do checklist (adicione, edite ou remova aqui)"


@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo")
    inlines = [ChecklistItemInline]
