from django.urls import path

from . import views_lider

urlpatterns = [
    path("lider/clientes/", views_lider.meus_clientes, name="lider_meus_clientes"),
    path("lider/clientes/novo/", views_lider.criar_cliente, name="lider_criar_cliente"),
    path("lider/clientes/<int:pk>/", views_lider.cliente_detalhe, name="lider_cliente_detalhe"),
    path("lider/clientes/<int:pk>/recibo/", views_lider.recibo_cliente, name="lider_recibo_cliente"),
    path("lider/medicao/", views_lider.medicao, name="lider_medicao"),
    path(
        "lider/medicao/<str:inicio>/<int:cliente_id>/",
        views_lider.medicao_cliente,
        name="lider_medicao_cliente",
    ),
    path(
        "lider/medicao/os/<int:os_pk>/custo-extra/<int:uso_id>/",
        views_lider.detalhe_custo_extra,
        name="lider_detalhe_custo_extra",
    ),
    path(
        "lider/medicao/os/<int:os_pk>/materiais/",
        views_lider.detalhe_materiais,
        name="lider_detalhe_materiais",
    ),
    path("lider/calculadora/", views_lider.calculadora, name="lider_calculadora"),
]
