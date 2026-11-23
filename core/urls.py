from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    # Público
    path("", views.inicio, name="inicio"),
    path("entrar/", views.EntrarView.as_view(), name="entrar"),
    path("sair/", LogoutView.as_view(), name="sair"),
    path("cadastro/", views.cadastro_sindico, name="cadastro_sindico"),
    path("convite/<str:codigo>/", views.convite, name="convite"),
    # Todos os usuários aprovados
    path("perfil/", views.meu_perfil, name="meu_perfil"),
    path("chamados/", views.chamado_lista, name="chamado_lista"),
    path("chamados/novo/", views.chamado_novo, name="chamado_novo"),
    path("chamados/<int:pk>/", views.chamado_detalhe, name="chamado_detalhe"),
    path("chamados/<int:pk>/afetado/", views.chamado_afetado, name="chamado_afetado"),
    path("chamados/<int:pk>/cancelar/", views.chamado_cancelar, name="chamado_cancelar"),
    path("chamados/<int:pk>/rito/<str:etapa>/", views.chamado_etapa, name="chamado_etapa"),
    # Só o síndico
    path("chamados/<int:pk>/editar/", views.chamado_editar, name="chamado_editar"),
    path("chamados/<int:pk>/excluir/", views.chamado_excluir, name="chamado_excluir"),
    path("condominio/", views.condominio_config, name="condominio"),
    path("condominio/convite/novo/", views.convite_novo, name="convite_novo"),
    path("condominio/convite/imprimir/", views.convite_imprimir, name="convite_imprimir"),
    path("condominio/unidades/", views.unidades, name="unidades"),
    path("condominio/unidades/<int:pk>/excluir/", views.unidade_excluir, name="unidade_excluir"),
    path("moradores/", views.moradores, name="moradores"),
    path("moradores/<int:pk>/", views.morador_editar, name="morador_editar"),
    path("moradores/<int:pk>/aprovar/", views.morador_aprovar, name="morador_aprovar"),
    path("moradores/<int:pk>/recusar/", views.morador_recusar, name="morador_recusar"),
    path("moradores/<int:pk>/remover/", views.morador_remover, name="morador_remover"),
]
