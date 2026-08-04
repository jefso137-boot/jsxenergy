from django.contrib import admin

from .models import ChecklistItem, ChecklistTemplate


class ChecklistItemInline(admin.TabularInline):
    model = ChecklistItem
    extra = 1
    fields = ("ordem", "descricao", "tipo_campo", "obrigatorio")


@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo")
    inlines = [ChecklistItemInline]


@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = ("descricao", "template", "tipo_campo", "ordem", "obrigatorio")
    list_filter = ("template", "tipo_campo")
    search_fields = ("descricao",)
