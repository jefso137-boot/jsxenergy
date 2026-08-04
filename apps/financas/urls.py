from django.urls import path

from . import views_lider

urlpatterns = [
    path("lider/financas/", views_lider.financas, name="lider_financas"),
]
