from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="chamado_lista"), name="inicio"),
    path("chamados/", views.chamado_lista, name="chamado_lista"),
    path("chamados/novo/", views.chamado_novo, name="chamado_novo"),
    path("chamados/<int:pk>/", views.chamado_detalhe, name="chamado_detalhe"),
    path("condominios/", views.condominio_lista, name="condominio_lista"),
    path("condominios/novo/", views.condominio_novo, name="condominio_novo"),
    path("condominios/<int:condominio_id>/chamados/novo/", views.chamado_abrir, name="chamado_abrir"),
]
