from django import forms
from django.core.exceptions import ValidationError

from .models import Chamado, Condominio


def validar_unidades(condominio, unidades):
    """As unidades solicitantes precisam pertencer ao condomínio do chamado."""
    if condominio and unidades and any(u.condominio_id != condominio.pk for u in unidades):
        raise ValidationError({"unidades": "Escolha apenas unidades deste condomínio."})


class FormBase(forms.ModelForm):
    """Rótulos sem ":" no final e classe CSS nos campos obrigatórios."""

    required_css_class = "obrigatorio"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)


class CondominioForm(FormBase):
    class Meta:
        model = Condominio
        fields = ["nome", "endereco", "numero_unidades", "sindico_nome", "sindico_telefone", "sindico_email"]
        help_texts = {"numero_unidades": "As unidades serão criadas automaticamente, numeradas de 1 a N."}
        widgets = {
            "nome": forms.TextInput(attrs={"placeholder": "Ex.: Residencial Jardim das Flores"}),
            "endereco": forms.TextInput(attrs={"placeholder": "Rua, número, bairro, cidade"}),
            "numero_unidades": forms.NumberInput(attrs={"min": 1, "max": 500}),
            "sindico_telefone": forms.TextInput(attrs={"inputmode": "tel", "placeholder": "(41) 99999-9999"}),
        }


class ChamadoForm(FormBase):
    class Meta:
        model = Chamado
        fields = ["solicitante_nome", "unidades", "tipo", "urgencia", "descricao"]
        widgets = {
            "unidades": forms.CheckboxSelectMultiple,
            "urgencia": forms.RadioSelect,
            "descricao": forms.Textarea(attrs={"rows": 4, "placeholder": "Descreva o problema"}),
        }

    def __init__(self, *args, condominio, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo"].choices = [("", "Selecione o tipo")] + Chamado.TIPOS
        # Só as unidades deste condomínio podem ser escolhidas.
        self.fields["unidades"].queryset = condominio.unidades.all()
        self.instance.condominio = condominio


class AtendimentoForm(FormBase):
    """Usado na tela do chamado para alterar status e urgência."""

    class Meta:
        model = Chamado
        fields = ["status", "urgencia"]
