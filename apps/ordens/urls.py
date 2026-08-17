from django.urls import path

from . import views_lider, views_tecnico

urlpatterns = [
    path("tecnico/minhas-os/", views_tecnico.minhas_os, name="tecnico_minhas_os"),
    path("tecnico/os/<int:pk>/", views_tecnico.detalhe_os, name="tecnico_detalhe_os"),
    path("lider/minhas-os/", views_lider.minhas_os, name="lider_minhas_os"),
    path("lider/os/nova/", views_lider.criar_os, name="lider_criar_os"),
    path("lider/os/<int:pk>/", views_lider.detalhe_os, name="lider_detalhe_os"),
    path("lider/os/<int:pk>/editar/", views_lider.editar_os, name="lider_editar_os"),
    path("lider/os/<int:pk>/excluir/", views_lider.excluir_os, name="lider_excluir_os"),
]
