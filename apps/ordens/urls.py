from django.urls import path

from . import views_tecnico

urlpatterns = [
    path("tecnico/minhas-os/", views_tecnico.minhas_os, name="tecnico_minhas_os"),
    path("tecnico/os/<int:pk>/", views_tecnico.detalhe_os, name="tecnico_detalhe_os"),
]
