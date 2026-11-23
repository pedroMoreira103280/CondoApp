from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .acesso import perfil_obrigatorio, sindico_obrigatorio
from .forms import (
    AtendimentoForm, CadastroMoradorForm, CadastroSindicoForm, ChamadoEdicaoForm, ChamadoForm,
    CondominioForm, EtapaForm, LoginForm, MeuPerfilForm, NovaUnidadeForm, RenomearUnidadesForm,
    SenhaNovaForm, UsuarioSindicoForm,
)
from .models import Andamento, Chamado, Condominio, Perfil


# ---------- Público: início, login e cadastros ----------

def inicio(request):
    if request.user.is_authenticated and hasattr(request.user, "perfil"):
        return redirect("chamado_lista")
    return render(request, "core/inicio.html")


class EntrarView(LoginView):
    template_name = "core/entrar.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


def cadastro_sindico(request):
    """Implantação em uma tarde: conta + condomínio + unidades num passo só."""
    if request.user.is_authenticated:
        return redirect("chamado_lista")
    form = CadastroSindicoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            usuario = form.save()
        login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
        c = usuario.perfil.condominio
        messages.success(request, f"{c} criado com {c.numero_unidades} unidades. Agora convide os moradores.")
        return redirect("condominio")
    return render(request, "core/cadastro_sindico.html", {"form": form})


def convite(request, codigo):
    """Cadastro do morador pelo link ou QR Code de convite."""
    condominio = get_object_or_404(Condominio, codigo_convite=codigo)
    if request.user.is_authenticated:
        return redirect("chamado_lista")
    form = CadastroMoradorForm(request.POST or None, condominio=condominio)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            form.save()
        return render(request, "core/convite_enviado.html", {"condominio": condominio})
    return render(request, "core/convite.html", {"form": form, "condominio": condominio})


# ---------- Meu perfil ----------

@perfil_obrigatorio
def meu_perfil(request):
    perfil = request.perfil
    dados = MeuPerfilForm(request.POST if "dados" in request.POST else None, perfil=perfil)
    senha = PasswordChangeForm(request.user, request.POST if "senha" in request.POST else None, label_suffix="")
    if request.method == "POST":
        if "dados" in request.POST and dados.is_valid():
            dados.save()
            messages.success(request, "Dados atualizados.")
            return redirect("meu_perfil")
        if "senha" in request.POST and senha.is_valid():
            senha.save()
            update_session_auth_hash(request, senha.user)
            messages.success(request, "Senha alterada.")
            return redirect("meu_perfil")
    return render(request, "core/meu_perfil.html", {"form_dados": dados, "form_senha": senha})


# ---------- Chamados ----------

ENCERRADOS = ("concluido", "cancelado")


def _chamado_ou_404(request, pk):
    """Busca o chamado só entre os que o usuário pode ver (nunca de outro condomínio)."""
    chamado = get_object_or_404(
        Chamado.objects.select_related("condominio", "unidade_envolvida", "criado_por__perfil")
        .prefetch_related("unidades", "afetados"),
        pk=pk, condominio=request.perfil.condominio,
    )
    relacao = chamado.relacao(request.perfil)
    if relacao is None:
        raise Http404
    return chamado, relacao


def _nome_autor(andamento, relacao, perfil):
    """Privacidade: moradores não veem o nome de outros moradores no histórico."""
    autor = andamento.autor
    if autor is None:
        return "Sistema"
    if autor.pk == perfil.usuario_id:
        return "Você"
    autor_perfil = getattr(autor, "perfil", None)
    if autor_perfil and autor_perfil.eh_sindico:
        return f"{autor_perfil.nome} (síndico)"
    if relacao == "sindico":
        return autor_perfil.nome if autor_perfil else autor.get_username()
    return "Um morador"


def _proximas_etapas(chamado, relacao):
    """Passos do rito disponíveis agora para este usuário."""
    if not chamado.unidade_envolvida_id or chamado.encerrado:
        return []
    if relacao == "sindico":
        return {"": ["aviso"], "aviso": ["notificacao", "decisao"], "notificacao": ["decisao"], "defesa": ["decisao"]}.get(chamado.etapa, [])
    if relacao == "envolvido" and chamado.etapa == "notificacao":
        return ["defesa"]
    return []


TEXTO_ETAPA = {
    "aviso": ("Enviar aviso amigável", "Primeiro passo: um lembrete educado da regra, sem expor quem registrou."),
    "notificacao": ("Enviar notificação formal", "Se o problema continuar. A unidade poderá apresentar defesa."),
    "defesa": ("Apresentar defesa", "Explique o seu lado. O síndico lê antes de decidir."),
    "decisao": ("Registrar decisão", "Encerra o caso. Advertência e multa só depois da notificação."),
}


def _render_detalhe(request, chamado, relacao, form_atendimento=None, form_etapa=None):
    perfil = request.perfil
    historico = [
        {"obj": a, "autor": _nome_autor(a, relacao, perfil)}
        for a in Andamento.visiveis(chamado, relacao)
    ]
    etapas = []
    for etapa in _proximas_etapas(chamado, relacao):
        form = form_etapa if form_etapa and form_etapa.etapa == etapa else EtapaForm(etapa=etapa, chamado=chamado, prefix=etapa)
        titulo, ajuda = TEXTO_ETAPA[etapa]
        etapas.append({"etapa": etapa, "form": form, "titulo": titulo, "ajuda": ajuda})
    contexto = {
        "chamado": chamado,
        "relacao": relacao,
        "historico": historico,
        "etapas": etapas,
        "form": form_atendimento or (AtendimentoForm(instance=chamado) if relacao == "sindico" else None),
        "ja_afetado": chamado.ja_afetado(request.user),
        "pode_marcar_afetado": relacao == "vizinho" and not chamado.encerrado and not chamado.privado,
        "pode_cancelar": relacao == "solicitante" and chamado.status == "aberto" and chamado.criado_por_id == request.user.pk,
    }
    return render(request, "core/chamado_detalhe.html", contexto)


@perfil_obrigatorio
def chamado_lista(request):
    perfil = request.perfil
    chamados = Chamado.visiveis_para(perfil).select_related("condominio", "unidade_envolvida").prefetch_related("unidades", "afetados")

    filtros = {}
    status = request.GET.get("status", "")
    if status in dict(Chamado.STATUS):
        chamados = chamados.filter(status=status)
        filtros["status"] = status
    for campo, opcoes in (("tipo", Chamado.TIPOS), ("local", Chamado.LOCAIS)):
        valor = request.GET.get(campo, "")
        if valor in dict(opcoes):
            chamados = chamados.filter(**{campo: valor})
            filtros[campo] = valor
    escopo = request.GET.get("escopo", "")
    if escopo == "meus" and not perfil.eh_sindico:
        meus = Q(criado_por=request.user) | Q(afetados=request.user)
        if perfil.unidade_id:
            meus |= Q(unidades=perfil.unidade_id)
        chamados = chamados.filter(meus).distinct()
    else:
        escopo = ""

    itens = [{"obj": c, "relacao": c.relacao(perfil)} for c in chamados]
    contexto = {
        "itens": itens,
        "status_atual": filtros.get("status", ""),
        "opcoes_status": Chamado.STATUS,
        "escopo": escopo,
        "filtro_tipo": dict(Chamado.TIPOS).get(filtros.get("tipo")),
        "filtro_local": dict(Chamado.LOCAIS).get(filtros.get("local")),
    }
    if perfil.eh_sindico:
        contexto["sugestoes"] = perfil.condominio.sugestoes_preventiva()
    return render(request, "core/chamado_lista.html", contexto)


@perfil_obrigatorio
def chamado_novo(request):
    perfil = request.perfil
    form = ChamadoForm(request.POST or None, perfil=perfil)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            chamado = form.save()
            texto = f"Registrado pelo síndico em nome de {chamado.solicitante_nome}." if chamado.registrado_pelo_sindico else ""
            Andamento.objects.create(chamado=chamado, autor=request.user, tipo="abertura", texto=texto)
        messages.success(request, f"Chamado #{chamado.pk} aberto.")
        return redirect("chamado_detalhe", chamado.pk)
    # Ocorrências inteligentes: mostra chamados parecidos em aberto antes de duplicar.
    parecidos = (
        Chamado.visiveis_para(perfil).filter(privado=False).exclude(status__in=ENCERRADOS)
        .prefetch_related("afetados")[:30]
    )
    return render(request, "core/chamado_form.html", {"form": form, "parecidos": parecidos})


@perfil_obrigatorio
def chamado_detalhe(request, pk):
    chamado, relacao = _chamado_ou_404(request, pk)
    if request.method == "POST":
        if relacao != "sindico":
            raise Http404
        antes = {"status": chamado.get_status_display(), "urgencia": chamado.get_urgencia_display()}
        form = AtendimentoForm(request.POST, instance=chamado)
        if form.is_valid():
            with transaction.atomic():
                chamado = form.save()
                for campo in form.changed_data:
                    depois = getattr(chamado, f"get_{campo}_display")()
                    Andamento.objects.create(chamado=chamado, autor=request.user, tipo=campo, texto=f"{antes[campo]} → {depois}")
            messages.success(request, "Atendimento atualizado.")
            return redirect("chamado_detalhe", chamado.pk)
        return _render_detalhe(request, chamado, relacao, form_atendimento=form)
    return _render_detalhe(request, chamado, relacao)


@perfil_obrigatorio
@require_POST
def chamado_afetado(request, pk):
    """"Também estou afetado": soma o morador ao chamado em vez de abrir outro igual."""
    chamado, relacao = _chamado_ou_404(request, pk)
    if relacao != "vizinho" or chamado.encerrado or chamado.privado:
        raise Http404
    if not chamado.ja_afetado(request.user):
        chamado.afetados.add(request.user)
        unidade = request.perfil.unidade
        Andamento.objects.create(
            chamado=chamado, autor=request.user, tipo="afetado",
            texto=f"Unidade {unidade} também está afetada." if unidade else "",
        )
        messages.success(request, "Registramos que você também está afetado. O síndico verá o total.")
    return redirect("chamado_detalhe", chamado.pk)


@perfil_obrigatorio
@require_POST
def chamado_cancelar(request, pk):
    chamado, relacao = _chamado_ou_404(request, pk)
    if relacao != "solicitante" or chamado.criado_por_id != request.user.pk or chamado.status != "aberto":
        raise Http404
    chamado.status = "cancelado"
    chamado.save(update_fields=["status"])
    Andamento.objects.create(chamado=chamado, autor=request.user, tipo="status", texto="Aberto → Cancelado (pelo próprio solicitante)")
    messages.success(request, "Chamado cancelado.")
    return redirect("chamado_detalhe", chamado.pk)


@perfil_obrigatorio
@require_POST
def chamado_etapa(request, pk, etapa):
    """Avança o rito: aviso → notificação → defesa → decisão."""
    chamado, relacao = _chamado_ou_404(request, pk)
    if etapa not in _proximas_etapas(chamado, relacao):
        raise Http404
    form = EtapaForm(request.POST, etapa=etapa, chamado=chamado, prefix=etapa)
    if not form.is_valid():
        return _render_detalhe(request, chamado, relacao, form_etapa=form)
    with transaction.atomic():
        texto = form.cleaned_data["texto"]
        if etapa == "decisao":
            chamado.resultado = form.cleaned_data["resultado"]
            texto = f"{chamado.get_resultado_display()}. {texto}"
        Andamento.objects.create(chamado=chamado, autor=request.user, tipo=etapa, texto=texto)
        status_antes = chamado.get_status_display()
        chamado.etapa = etapa
        if etapa == "decisao":
            chamado.status = "concluido"
        elif chamado.status == "aberto":
            chamado.status = "andamento"
        chamado.save()
        if chamado.get_status_display() != status_antes:
            Andamento.objects.create(chamado=chamado, autor=request.user, tipo="status", texto=f"{status_antes} → {chamado.get_status_display()}")
    messages.success(request, {"aviso": "Aviso enviado à unidade.", "notificacao": "Notificação registrada.",
                               "defesa": "Defesa enviada ao síndico.", "decisao": "Decisão registrada. Caso encerrado."}[etapa])
    return redirect("chamado_detalhe", chamado.pk)


@sindico_obrigatorio
def chamado_editar(request, pk):
    chamado, _ = _chamado_ou_404(request, pk)
    form = ChamadoEdicaoForm(request.POST or None, instance=chamado)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            form.save()
            if form.changed_data:
                campos = ", ".join(str(form.fields[c].label).lower() for c in form.changed_data)
                Andamento.objects.create(chamado=chamado, autor=request.user, tipo="edicao", texto=f"Campos alterados: {campos}.")
        messages.success(request, "Chamado atualizado.")
        return redirect("chamado_detalhe", chamado.pk)
    return render(request, "core/chamado_editar.html", {"form": form, "chamado": chamado})


@sindico_obrigatorio
def chamado_excluir(request, pk):
    chamado, _ = _chamado_ou_404(request, pk)
    if request.method == "POST":
        chamado.delete()
        messages.success(request, f"Chamado #{pk} excluído.")
        return redirect("chamado_lista")
    return render(request, "core/confirmar.html", {
        "titulo": f"Excluir o chamado #{pk}?",
        "texto": "O chamado e todo o histórico dele serão apagados. Para só encerrar, use o status Cancelado.",
        "voltar": reverse("chamado_detalhe", args=[pk]),
        "botao": "Excluir chamado",
    })


# ---------- Condomínio e unidades (síndico) ----------

def _link_convite(request, condominio):
    return request.build_absolute_uri(reverse("convite", args=[condominio.codigo_convite]))


@sindico_obrigatorio
def condominio_config(request):
    condominio = request.perfil.condominio
    form = CondominioForm(request.POST or None, instance=condominio)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Dados do condomínio salvos.")
        return redirect("condominio")

    # Implantação em uma tarde: passos e tempo até o primeiro chamado.
    primeiro = condominio.chamados.order_by("data_abertura").first()
    moradores = condominio.perfis.filter(papel=Perfil.MORADOR, aprovado=True).count()
    passos = [
        ("Condomínio e unidades criados", True),
        ("Unidades com o nome certo (ex.: Bloco A - 101)", condominio.unidades.exclude(identificador__regex=r"^\d+$").exists()),
        ("Convite enviado e primeiro morador aprovado", moradores > 0),
        ("Primeiro chamado registrado", primeiro is not None),
    ]
    contexto = {
        "form": form,
        "condominio": condominio,
        "link": _link_convite(request, condominio),
        "passos": passos,
        "data_primeiro": primeiro.data_abertura if primeiro else None,
        "total_moradores": moradores,
        "unidades_com_morador": condominio.unidades.filter(moradores__aprovado=True).distinct().count(),
    }
    return render(request, "core/condominio.html", contexto)


@sindico_obrigatorio
@require_POST
def convite_novo(request):
    request.perfil.condominio.novo_convite()
    messages.success(request, "Novo link de convite gerado. O link anterior não funciona mais.")
    return redirect("condominio")


@sindico_obrigatorio
def convite_imprimir(request):
    """Aviso para imprimir QR Code (modo híbrido)."""
    condominio = request.perfil.condominio
    return render(request, "core/convite_imprimir.html", {
        "condominio": condominio, "link": _link_convite(request, condominio), "sindicos": condominio.sindicos,
    })


@sindico_obrigatorio
def unidades(request):
    condominio = request.perfil.condominio
    renomear = RenomearUnidadesForm(request.POST if "renomear" in request.POST else None, condominio=condominio)
    nova = NovaUnidadeForm(request.POST if "nova" in request.POST else None, condominio=condominio)
    if request.method == "POST":
        if "renomear" in request.POST and renomear.is_valid():
            with transaction.atomic():
                renomear.save()
            messages.success(request, "Unidades renomeadas.")
            return redirect("unidades")
        if "nova" in request.POST and nova.is_valid():
            unidade = nova.save()
            messages.success(request, f"Unidade {unidade} criada.")
            return redirect("unidades")
    lista = condominio.unidades.annotate(
        total_moradores=Count("moradores", filter=Q(moradores__aprovado=True), distinct=True),
        total_chamados=Count("chamados", distinct=True),
    )
    return render(request, "core/unidades.html", {"form_renomear": renomear, "form_nova": nova, "unidades": lista})


@sindico_obrigatorio
@require_POST
def unidade_excluir(request, pk):
    condominio = request.perfil.condominio
    unidade = get_object_or_404(condominio.unidades, pk=pk)
    if unidade.em_uso:
        messages.error(request, f"A unidade {unidade} tem moradores ou chamados e não pode ser excluída.")
    elif condominio.unidades.count() == 1:
        messages.error(request, "O condomínio precisa de pelo menos uma unidade.")
    else:
        unidade.delete()
        condominio.atualizar_total_unidades()
        messages.success(request, f"Unidade {unidade} excluída.")
    return redirect("unidades")


# ---------- Moradores (síndico) ----------

def _perfil_do_condominio(request, pk):
    return get_object_or_404(Perfil.objects.select_related("usuario", "unidade"), pk=pk, condominio=request.perfil.condominio)


@sindico_obrigatorio
def moradores(request):
    perfis = request.perfil.condominio.perfis.select_related("usuario", "unidade")
    return render(request, "core/moradores.html", {
        "aguardando": perfis.filter(aprovado=False),
        "ativos": perfis.filter(aprovado=True, usuario__is_active=True),
        "bloqueados": perfis.filter(aprovado=True, usuario__is_active=False),
    })


@sindico_obrigatorio
@require_POST
def morador_aprovar(request, pk):
    perfil = _perfil_do_condominio(request, pk)
    perfil.aprovado = True
    perfil.save(update_fields=["aprovado"])
    messages.success(request, f"{perfil.nome} aprovado. Já pode entrar no CondoApp.")
    return redirect("moradores")


@sindico_obrigatorio
@require_POST
def morador_recusar(request, pk):
    perfil = _perfil_do_condominio(request, pk)
    if perfil.aprovado:
        raise Http404
    nome = perfil.nome
    perfil.usuario.delete()
    messages.success(request, f"Cadastro de {nome} recusado.")
    return redirect("moradores")


@sindico_obrigatorio
def morador_editar(request, pk):
    alvo = _perfil_do_condominio(request, pk)
    form = UsuarioSindicoForm(request.POST if "dados" in request.POST else None, perfil=alvo, editor=request.perfil)
    senha = SenhaNovaForm(request.POST if "senha" in request.POST else None, usuario=alvo.usuario)
    if request.method == "POST":
        if "dados" in request.POST and form.is_valid():
            form.save()
            messages.success(request, f"Dados de {alvo.nome} salvos.")
            return redirect("moradores")
        if "senha" in request.POST and senha.is_valid():
            senha.save()
            if alvo.pk == request.perfil.pk:
                update_session_auth_hash(request, alvo.usuario)
            messages.success(request, f"Nova senha definida para {alvo.nome}. Entregue a senha pessoalmente.")
            return redirect("moradores")
    return render(request, "core/morador_editar.html", {"alvo": alvo, "form": form, "form_senha": senha})


@sindico_obrigatorio
def morador_remover(request, pk):
    alvo = _perfil_do_condominio(request, pk)
    if alvo.pk == request.perfil.pk:
        messages.error(request, "Você não pode remover a sua própria conta.")
        return redirect("moradores")
    if request.method == "POST":
        nome = alvo.nome
        alvo.usuario.delete()
        messages.success(request, f"Conta de {nome} removida. Os chamados dela continuam no histórico.")
        return redirect("moradores")
    return render(request, "core/confirmar.html", {
        "titulo": f"Remover a conta de {alvo.nome}?",
        "texto": "A pessoa perde o acesso e a conta é apagada. Os chamados continuam no histórico. "
                 "Para só bloquear o acesso, edite a conta e desmarque \"Acesso liberado\".",
        "voltar": reverse("morador_editar", args=[alvo.pk]),
        "botao": "Remover conta",
    })
