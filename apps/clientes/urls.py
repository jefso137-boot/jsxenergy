from django.urls import path

from . import views_lider

urlpatterns = [
    path("lider/clientes/", views_lider.meus_clientes, name="lider_meus_clientes"),
    path("lider/clientes/novo/", views_lider.criar_cliente, name="lider_criar_cliente"),
]
