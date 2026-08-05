from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.contas.urls")),
    path("", include("apps.ordens.urls")),
    path("", include("apps.clientes.urls")),
]

admin.site.site_header = "JSX Energy — Painel Administrativo"
admin.site.site_title = "JSX Energy ERP"
admin.site.index_title = "Gestão de Ordens de Serviço"

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
