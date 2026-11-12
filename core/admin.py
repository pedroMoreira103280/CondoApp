from django import forms
from django.contrib import admin

from .forms import validar_unidades
from .models import Chamado, Condominio, Unidade

admin.site.site_header = "CondoApp — administração"
admin.site.site_title = "CondoApp"


class UnidadeInline(admin.TabularInline):
    """Permite só renomear as unidades geradas (ex.: "Bloco A - 101")."""

    model = Unidade
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Condominio)
class CondominioAdmin(admin.ModelAdmin):
    list_display = ["nome", "endereco", "numero_unidades", "sindico_nome"]
    search_fields = ["nome", "endereco", "sindico_nome"]
    inlines = [UnidadeInline]

    def get_readonly_fields(self, request, obj=None):
        # As unidades são geradas no cadastro; depois o número fica fixo.
        return ["numero_unidades"] if obj else []


class ChamadoAdminForm(forms.ModelForm):
    def clean(self):
        dados = super().clean()
        validar_unidades(dados.get("condominio"), dados.get("unidades"))
        return dados


@admin.register(Chamado)
class ChamadoAdmin(admin.ModelAdmin):
    form = ChamadoAdminForm
    list_display = ["id", "tipo", "condominio", "urgencia", "status", "solicitante_nome", "data_abertura"]
    list_filter = ["status", "urgencia", "tipo", "condominio"]
    search_fields = ["solicitante_nome", "descricao"]
    filter_horizontal = ["unidades"]
