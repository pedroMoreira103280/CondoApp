from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from .models import Chamado, Condominio, Perfil, Unidade

User = get_user_model()


def validar_unidades(condominio, unidades):
    """As unidades solicitantes precisam pertencer ao condomínio do chamado."""
    if condominio and unidades and any(u.condominio_id != condominio.pk for u in unidades):
        raise ValidationError({"unidades": "Escolha apenas unidades deste condomínio."})


class Rotulos:
    """Rótulos sem ":" no final e classe CSS nos campos obrigatórios."""

    required_css_class = "obrigatorio"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)


class FormBase(Rotulos, forms.ModelForm):
    pass


class FormSimples(Rotulos, forms.Form):
    pass


# ---------- Contas ----------

class LoginForm(Rotulos, AuthenticationForm):
    """Entrar com e-mail e senha. Morador só entra depois de aprovado pelo síndico."""

    username = forms.EmailField(label="E-mail", widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}))

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "E-mail ou senha incorretos.",
        "pendente": "Seu cadastro ainda aguarda a aprovação do síndico.",
    }

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        perfil = getattr(user, "perfil", None)
        if perfil and not perfil.aprovado:
            raise ValidationError(self.error_messages["pendente"], code="pendente")


class ContaForm(FormSimples):
    """Dados de acesso comuns ao cadastro de síndico e de morador."""

    nome = forms.CharField(label="Nome completo", max_length=150, widget=forms.TextInput(attrs={"autocomplete": "name"}))
    email = forms.EmailField(label="E-mail", widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    telefone = forms.CharField(
        label="Telefone", max_length=20, required=False,
        widget=forms.TextInput(attrs={"inputmode": "tel", "placeholder": "(41) 99999-9999", "autocomplete": "tel"}),
    )
    senha = forms.CharField(
        label="Senha", strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Pelo menos 8 caracteres, sem ser só números.",
    )
    senha2 = forms.CharField(label="Repita a senha", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(username=email).exists():
            raise ValidationError("Já existe uma conta com este e-mail.")
        return email

    def clean(self):
        dados = super().clean()
        senha, senha2 = dados.get("senha"), dados.get("senha2")
        if senha and senha2 and senha != senha2:
            self.add_error("senha2", "As senhas não conferem.")
        elif senha:
            usuario = User(username=dados.get("email", ""), email=dados.get("email", ""), first_name=dados.get("nome", ""))
            try:
                password_validation.validate_password(senha, usuario)
            except ValidationError as erro:
                self.add_error("senha", erro)
        return dados

    def criar_usuario(self):
        d = self.cleaned_data
        primeiro, _, resto = d["nome"].strip().partition(" ")
        return User.objects.create_user(
            username=d["email"], email=d["email"], password=d["senha"], first_name=primeiro, last_name=resto
        )


class CadastroSindicoForm(ContaForm):
    """Implantação em uma tarde: conta do síndico + condomínio + unidades num formulário só."""

    condominio_nome = forms.CharField(
        label="Nome do condomínio", max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "Ex.: Residencial Jardim das Flores"}),
    )
    endereco = forms.CharField(label="Endereço", max_length=200, widget=forms.TextInput(attrs={"placeholder": "Rua, número, bairro, cidade"}))
    numero_unidades = forms.IntegerField(
        label="Número de casas/apartamentos", min_value=1, max_value=500,
        help_text="As unidades são criadas na hora, numeradas de 1 a N. Você pode renomeá-las depois (ex.: \"Bloco A - 101\").",
    )
    field_order = ["condominio_nome", "endereco", "numero_unidades", "nome", "email", "telefone", "senha", "senha2"]

    def save(self):
        d = self.cleaned_data
        condominio = Condominio.objects.create(nome=d["condominio_nome"], endereco=d["endereco"], numero_unidades=d["numero_unidades"])
        usuario = self.criar_usuario()
        Perfil.objects.create(usuario=usuario, condominio=condominio, papel=Perfil.SINDICO, telefone=d["telefone"], aprovado=True)
        return usuario


class CadastroMoradorForm(ContaForm):
    """Cadastro pelo link de convite. O acesso é liberado depois da aprovação do síndico."""

    unidade = forms.ModelChoiceField(label="Sua casa/apartamento", queryset=Unidade.objects.none(), empty_label="Selecione")
    field_order = ["nome", "unidade", "email", "telefone", "senha", "senha2"]

    def __init__(self, *args, condominio, **kwargs):
        super().__init__(*args, **kwargs)
        self.condominio = condominio
        self.fields["unidade"].queryset = condominio.unidades.all()

    def save(self):
        usuario = self.criar_usuario()
        Perfil.objects.create(
            usuario=usuario, condominio=self.condominio, unidade=self.cleaned_data["unidade"],
            papel=Perfil.MORADOR, telefone=self.cleaned_data["telefone"], aprovado=False,
        )
        return usuario


class MeuPerfilForm(FormSimples):
    """O próprio usuário edita nome, e-mail e telefone. Unidade e papel só o síndico muda."""

    nome = forms.CharField(label="Nome completo", max_length=150)
    email = forms.EmailField(label="E-mail")
    telefone = forms.CharField(label="Telefone", max_length=20, required=False, widget=forms.TextInput(attrs={"inputmode": "tel"}))

    def __init__(self, *args, perfil, **kwargs):
        self.perfil = perfil
        u = perfil.usuario
        kwargs.setdefault("initial", {"nome": u.get_full_name(), "email": u.email, "telefone": perfil.telefone})
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(username=email).exclude(pk=self.perfil.usuario_id).exists():
            raise ValidationError("Já existe uma conta com este e-mail.")
        return email

    def save(self):
        d, u = self.cleaned_data, self.perfil.usuario
        u.first_name, _, u.last_name = d["nome"].strip().partition(" ")
        u.username = u.email = d["email"]
        u.save()
        self.perfil.telefone = d["telefone"]
        self.perfil.save()
        return self.perfil


class UsuarioSindicoForm(MeuPerfilForm):
    """Síndico edita qualquer usuário do condomínio: dados, unidade, papel e acesso."""

    unidade = forms.ModelChoiceField(label="Casa/apartamento", queryset=Unidade.objects.none(), required=False, empty_label="Sem unidade")
    papel = forms.ChoiceField(label="Perfil", choices=Perfil.PAPEIS)
    ativo = forms.BooleanField(label="Acesso liberado", required=False, help_text="Desmarque para bloquear o acesso sem apagar o histórico.")

    def __init__(self, *args, perfil, editor, **kwargs):
        kwargs.setdefault("initial", {
            "nome": perfil.usuario.get_full_name(), "email": perfil.usuario.email, "telefone": perfil.telefone,
            "unidade": perfil.unidade_id, "papel": perfil.papel, "ativo": perfil.usuario.is_active,
        })
        super().__init__(*args, perfil=perfil, **kwargs)
        self.editor = editor
        self.fields["unidade"].queryset = perfil.condominio.unidades.all()

    def clean(self):
        dados = super().clean()
        if self.perfil.pk == self.editor.pk:
            # Evita que o síndico se tranque fora do próprio condomínio.
            if dados.get("papel") != Perfil.SINDICO:
                self.add_error("papel", "Você não pode tirar o seu próprio perfil de síndico.")
            if not dados.get("ativo"):
                self.add_error("ativo", "Você não pode bloquear o seu próprio acesso.")
        if dados.get("papel") == Perfil.MORADOR and not dados.get("unidade"):
            self.add_error("unidade", "Morador precisa estar ligado a uma casa/apartamento.")
        return dados

    def save(self):
        perfil = super().save()
        d = self.cleaned_data
        perfil.unidade = d["unidade"]
        perfil.papel = d["papel"]
        perfil.save()
        perfil.usuario.is_active = d["ativo"]
        perfil.usuario.save(update_fields=["is_active"])
        return perfil


class SenhaNovaForm(FormSimples):
    """Síndico define uma nova senha para um morador (ex.: quem esqueceu e não usa e-mail)."""

    senha = forms.CharField(label="Nova senha", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

    def clean_senha(self):
        senha = self.cleaned_data["senha"]
        password_validation.validate_password(senha, self.usuario)
        return senha

    def save(self):
        self.usuario.set_password(self.cleaned_data["senha"])
        self.usuario.save()


# ---------- Condomínio e unidades (síndico) ----------

class CondominioForm(FormBase):
    class Meta:
        model = Condominio
        fields = ["nome", "endereco"]
        widgets = {"endereco": forms.TextInput(attrs={"placeholder": "Rua, número, bairro, cidade"})}


class RenomearUnidadesForm(FormSimples):
    """Renomeia todas as unidades de uma vez: um identificador por linha, na mesma ordem."""

    identificadores = forms.CharField(label="Identificadores", widget=forms.Textarea(attrs={"rows": 12, "spellcheck": "false"}))

    def __init__(self, *args, condominio, **kwargs):
        self.unidades = list(condominio.unidades.all())
        kwargs.setdefault("initial", {"identificadores": "\n".join(u.identificador for u in self.unidades)})
        super().__init__(*args, **kwargs)
        self.fields["identificadores"].help_text = (
            f"Uma unidade por linha, na ordem atual ({len(self.unidades)} linhas). Ex.: Bloco A - 101."
        )

    def clean_identificadores(self):
        linhas = [linha.strip() for linha in self.cleaned_data["identificadores"].splitlines() if linha.strip()]
        if len(linhas) != len(self.unidades):
            raise ValidationError(
                f"São {len(self.unidades)} unidades e você informou {len(linhas)} linhas. "
                "Para criar ou excluir unidades, use os botões abaixo."
            )
        repetidos = sorted({x for x in linhas if linhas.count(x) > 1})
        if repetidos:
            raise ValidationError(f"Identificadores repetidos: {', '.join(repetidos)}.")
        if any(len(x) > 30 for x in linhas):
            raise ValidationError("Cada identificador pode ter no máximo 30 caracteres.")
        return linhas

    def save(self):
        novos = self.cleaned_data["identificadores"]
        # Dois passos para não colidir com a regra de nome único durante a troca.
        for unidade in self.unidades:
            unidade.identificador = f"__tmp_{unidade.pk}"
        Unidade.objects.bulk_update(self.unidades, ["identificador"])
        for unidade, nome in zip(self.unidades, novos):
            unidade.identificador = nome
        Unidade.objects.bulk_update(self.unidades, ["identificador"])


class NovaUnidadeForm(FormSimples):
    identificador = forms.CharField(label="Nova unidade", max_length=30, widget=forms.TextInput(attrs={"placeholder": "Ex.: Casa 21"}))

    def __init__(self, *args, condominio, **kwargs):
        super().__init__(*args, **kwargs)
        self.condominio = condominio

    def clean_identificador(self):
        nome = self.cleaned_data["identificador"].strip()
        if self.condominio.unidades.filter(identificador=nome).exists():
            raise ValidationError("Já existe uma unidade com este nome.")
        return nome

    def save(self):
        unidade = self.condominio.unidades.create(identificador=self.cleaned_data["identificador"])
        self.condominio.atualizar_total_unidades()
        return unidade


# ---------- Chamados ----------

class ChamadoForm(FormBase):
    """Abrir chamado.

    Morador: a unidade é a dele, o nome vem da conta.
    Síndico: escolhe as unidades e pode registrar em nome de quem não usa o app (modo híbrido).
    """

    class Meta:
        model = Chamado
        fields = ["solicitante_nome", "unidades", "tipo", "local", "urgencia", "descricao", "unidade_envolvida", "privado"]
        labels = {"solicitante_nome": "Nome do morador"}
        widgets = {
            "unidades": forms.CheckboxSelectMultiple,
            "urgencia": forms.RadioSelect,
            "descricao": forms.Textarea(attrs={"rows": 4, "placeholder": "Descreva o problema"}),
        }

    def __init__(self, *args, perfil, **kwargs):
        super().__init__(*args, **kwargs)
        self.perfil = perfil
        condominio = perfil.condominio
        self.instance.condominio = condominio
        self.instance.criado_por = perfil.usuario
        self.fields["tipo"].choices = [("", "Selecione o tipo")] + Chamado.TIPOS
        self.fields["unidade_envolvida"].queryset = condominio.unidades.all()
        self.fields["unidade_envolvida"].empty_label = "Nenhuma"
        if perfil.eh_sindico:
            self.fields["unidades"].queryset = condominio.unidades.all()
            self.fields["solicitante_nome"].help_text = (
                "Registrando por quem não usa o app? Informe o nome dele e marque a unidade."
            )
            self.fields["solicitante_nome"].initial = perfil.nome
        else:
            # Morador só registra pela própria unidade, com o próprio nome.
            del self.fields["unidades"]
            del self.fields["solicitante_nome"]

    def clean(self):
        dados = super().clean()
        envolvida = dados.get("unidade_envolvida")
        unidades = dados.get("unidades") or ([self.perfil.unidade] if self.perfil.unidade_id else [])
        if envolvida and envolvida in unidades:
            self.add_error("unidade_envolvida", "A unidade envolvida não pode ser a mesma que registra.")
        if not self.perfil.eh_sindico and not self.perfil.unidade_id:
            raise ValidationError("Sua conta não está ligada a uma unidade. Fale com o síndico.")
        return dados

    def save(self, commit=True):
        if not self.perfil.eh_sindico:
            self.instance.solicitante_nome = self.perfil.nome
        chamado = super().save(commit=commit)
        if not self.perfil.eh_sindico:
            chamado.unidades.set([self.perfil.unidade])
        return chamado


class ChamadoEdicaoForm(FormBase):
    """Síndico edita todos os campos do chamado."""

    class Meta:
        model = Chamado
        fields = ["solicitante_nome", "unidades", "tipo", "local", "urgencia", "status", "descricao", "unidade_envolvida", "privado"]
        widgets = {
            "unidades": forms.CheckboxSelectMultiple,
            "urgencia": forms.RadioSelect,
            "descricao": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        unidades = self.instance.condominio.unidades.all()
        self.fields["unidades"].queryset = unidades
        self.fields["unidade_envolvida"].queryset = unidades
        self.fields["unidade_envolvida"].empty_label = "Nenhuma"

    def clean(self):
        dados = super().clean()
        validar_unidades(self.instance.condominio, dados.get("unidades"))
        envolvida = dados.get("unidade_envolvida")
        if envolvida and envolvida in (dados.get("unidades") or []):
            self.add_error("unidade_envolvida", "A unidade envolvida não pode ser a mesma que registra.")
        return dados


class AtendimentoForm(FormBase):
    """Usado na tela do chamado para o síndico alterar status e urgência."""

    class Meta:
        model = Chamado
        fields = ["status", "urgencia"]


class EtapaForm(FormSimples):
    """Um passo do rito: aviso, notificação, defesa ou decisão."""

    texto = forms.CharField(label="Mensagem", widget=forms.Textarea(attrs={"rows": 3}))
    resultado = forms.ChoiceField(label="Resultado", choices=Chamado.RESULTADOS[1:], required=False)

    def __init__(self, *args, etapa, chamado, **kwargs):
        super().__init__(*args, **kwargs)
        self.etapa, self.chamado = etapa, chamado
        if etapa != "decisao":
            del self.fields["resultado"]
        else:
            self.fields["resultado"].required = True

    def clean(self):
        dados = super().clean()
        # Direito de defesa: advertência ou multa só depois da notificação formal.
        if self.etapa == "decisao" and dados.get("resultado") in ("advertencia", "multa") and self.chamado.etapa not in ("notificacao", "defesa"):
            self.add_error("resultado", "Advertência ou multa só depois da notificação formal, para garantir o direito de defesa.")
        return dados
