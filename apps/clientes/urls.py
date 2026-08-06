from django.urls import path

from . import views_lider

urlpatterns = [
    path("lider/clientes/", views_lider.meus_clientes, name="lider_meus_clientes"),
    path("lider/clientes/novo/", views_lider.criar_cliente, name="lider_criar_cliente"),
    path("lider/clientes/<int:pk>/", views_lider.cliente_detalhe, name="lider_cliente_detalhe"),
    path("lider/clientes/<int:pk>/recibo/", views_lider.recibo_cliente, name="lider_recibo_cliente"),
    path("lider/medicao/", views_lider.medicao, name="lider_medicao"),
]
