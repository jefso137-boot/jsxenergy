from django.contrib import admin

from .models import ConfiguracaoPreco, CustoExtraCatalogo, MaterialCatalogo


@admin.register(ConfiguracaoPreco)
class ConfiguracaoPrecoAdmin(admin.ModelAdmin):
    list_display = ("valor_placa", "valor_padrao", "valor_vistoria", "atualizado_em")

    def has_add_permission(self, request):
        return not ConfiguracaoPreco.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MaterialCatalogo)
class MaterialCatalogoAdmin(admin.ModelAdmin):
    list_display = ("nome", "valor", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome",)


@admin.register(CustoExtraCatalogo)
class CustoExtraCatalogoAdmin(admin.ModelAdmin):
    list_display = ("nome", "valor", "tipo_campo", "ativo")
    list_filter = ("ativo", "tipo_campo")
    search_fields = ("nome",)
