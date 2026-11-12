from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AtendimentoForm, ChamadoForm, CondominioForm
from .models import Chamado, Condominio


# ---------- Condomínios ----------

def condominio_lista(request):
    condominios = Condominio.objects.annotate(total_chamados=Count("chamados"))
    return render(request, "core/condominio_lista.html", {"condominios": condominios})


def condominio_novo(request):
    form = CondominioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        condominio = form.save()
        messages.success(request, f"{condominio} cadastrado com {condominio.numero_unidades} unidades.")
        return redirect("condominio_lista")
    return render(request, "core/condominio_form.html", {"form": form})


# ---------- Chamados ----------

def chamado_lista(request):
    chamados = Chamado.objects.select_related("condominio").prefetch_related("unidades")
    status = request.GET.get("status", "")
    if status in dict(Chamado.STATUS):
        chamados = chamados.filter(status=status)
    else:
        status = ""
    contexto = {"chamados": chamados, "status_atual": status, "opcoes_status": Chamado.STATUS}
    return render(request, "core/chamado_lista.html", contexto)


def chamado_novo(request):
    """Primeiro passo: escolher o condomínio (pulado se só houver um)."""
    condominios = list(Condominio.objects.all())
    if len(condominios) == 1:
        return redirect("chamado_abrir", condominios[0].pk)
    return render(request, "core/chamado_escolher.html", {"condominios": condominios})


def chamado_abrir(request, condominio_id):
    condominio = get_object_or_404(Condominio, pk=condominio_id)
    form = ChamadoForm(request.POST or None, condominio=condominio)
    if request.method == "POST" and form.is_valid():
        chamado = form.save()
        messages.success(request, f"Chamado #{chamado.pk} aberto.")
        return redirect("chamado_detalhe", chamado.pk)
    return render(request, "core/chamado_form.html", {"form": form, "condominio": condominio})


def chamado_detalhe(request, pk):
    chamado = get_object_or_404(Chamado.objects.select_related("condominio"), pk=pk)
    form = AtendimentoForm(request.POST or None, instance=chamado)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Atendimento atualizado.")
        return redirect("chamado_detalhe", chamado.pk)
    return render(request, "core/chamado_detalhe.html", {"chamado": chamado, "form": form})
