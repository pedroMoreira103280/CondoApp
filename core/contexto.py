from .models import Perfil


def perfil(request):
    """Disponibiliza o perfil e o número de cadastros pendentes em todos os templates."""
    user = getattr(request, "user", None)
    perfil = getattr(user, "perfil", None) if user and user.is_authenticated else None
    pendentes = 0
    if perfil and perfil.aprovado and perfil.eh_sindico:
        pendentes = Perfil.objects.filter(condominio=perfil.condominio_id, aprovado=False).count()
    return {"perfil": perfil, "pendentes": pendentes}
