"""Regras de acesso: quem pode entrar em cada tela."""

from functools import wraps

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def perfil_obrigatorio(view):
    """Exige login, conta ativa e perfil aprovado num condomínio."""

    @wraps(view)
    def interna(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        perfil = getattr(user, "perfil", None)
        if perfil is None:
            # Ex.: superusuário criado pelo terminal, sem condomínio.
            if user.is_staff:
                return redirect("admin:index")
            logout(request)
            messages.error(request, "Esta conta não está ligada a nenhum condomínio.")
            return redirect("entrar")
        if not perfil.aprovado:
            logout(request)
            messages.error(request, "Seu cadastro ainda aguarda a aprovação do síndico.")
            return redirect("entrar")
        request.perfil = perfil
        return view(request, *args, **kwargs)

    return interna


def sindico_obrigatorio(view):
    """Telas de administração do condomínio: só o síndico."""

    @perfil_obrigatorio
    @wraps(view)
    def interna(request, *args, **kwargs):
        if not request.perfil.eh_sindico:
            raise PermissionDenied("Somente o síndico pode acessar esta página.")
        return view(request, *args, **kwargs)

    return interna
