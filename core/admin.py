from django import forms
from django.contrib import admin

from .forms import validar_unidades
from .models import Andamento, Chamado, Condominio, Perfil, Unidade

admin.site.site_header = "CondoApp — administração"
admin.site.site_title = "CondoApp"


class UnidadeInline(admin.TabularInline):
    """Permite só renomear as unidades (ex.: "Bloco A - 101")."""

    model = Unidade
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class PerfilInline(admin.TabularInline):
    model = Perfil
    extra = 0
    fields = ["usuario", "papel", "unidade", "telefone", "aprovado"]
    raw_id_fields = ["usuario"]


@admin.register(Condominio)
class CondominioAdmin(admin.ModelAdmin):
    list_display = ["nome", "endereco", "numero_unidades", "criado_em"]
    search_fields = ["nome", "endereco"]
    readonly_fields = ["numero_unidades", "codigo_convite", "criado_em"]
    inlines = [PerfilInline, UnidadeInline]

    def get_readonly_fields(self, request, obj=None):
        # No cadastro informa-se o número; depois ele acompanha as unidades.
        return self.readonly_fields if obj else ["codigo_convite", "criado_em"]


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ["nome", "papel", "condominio", "unidade", "aprovado"]
    list_filter = ["papel", "aprovado", "condominio"]
    search_fields = ["usuario__first_name", "usuario__last_name", "usuario__email"]
    raw_id_fields = ["usuario"]


class ChamadoAdminForm(forms.ModelForm):
    def clean(self):
        dados = super().clean()
        validar_unidades(dados.get("condominio"), dados.get("unidades"))
        return dados


class AndamentoInline(admin.TabularInline):
    model = Andamento
    extra = 0
    fields = ["data", "tipo", "autor", "texto"]
    readonly_fields = ["data"]


@admin.register(Chamado)
class ChamadoAdmin(admin.ModelAdmin):
    form = ChamadoAdminForm
    list_display = ["id", "tipo", "local", "condominio", "urgencia", "status", "privado", "etapa", "data_abertura"]
    list_filter = ["status", "urgencia", "tipo", "local", "privado", "etapa", "condominio"]
    search_fields = ["solicitante_nome", "descricao"]
    filter_horizontal = ["unidades", "afetados"]
    inlines = [AndamentoInline]
