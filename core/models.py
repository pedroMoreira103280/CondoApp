import secrets
from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone


def gerar_codigo_convite():
    return secrets.token_urlsafe(9)


class Condominio(models.Model):
    nome = models.CharField("nome", max_length=100)
    endereco = models.CharField("endereço", max_length=200)
    numero_unidades = models.PositiveIntegerField(
        "número de casas/apartamentos",
        validators=[MinValueValidator(1), MaxValueValidator(500)],
    )
    # Código do link de convite. Quem tem o link pede acesso; o síndico aprova.
    codigo_convite = models.CharField("código de convite", max_length=20, unique=True, default=gerar_codigo_convite)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "condomínio"
        verbose_name_plural = "condomínios"

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        novo = self.pk is None
        super().save(*args, **kwargs)
        if novo:
            # Gera as unidades 1..N automaticamente no cadastro.
            Unidade.objects.bulk_create(
                Unidade(condominio=self, identificador=str(n))
                for n in range(1, self.numero_unidades + 1)
            )

    def novo_convite(self):
        """Gera outro link de convite; o anterior deixa de funcionar."""
        self.codigo_convite = gerar_codigo_convite()
        self.save(update_fields=["codigo_convite"])

    def atualizar_total_unidades(self):
        self.numero_unidades = self.unidades.count()
        self.save(update_fields=["numero_unidades"])

    @property
    def sindicos(self):
        return self.perfis.filter(papel=Perfil.SINDICO, usuario__is_active=True).select_related("usuario")

    def sugestoes_preventiva(self, dias=90, minimo=3):
        """Reincidência: mesmo tipo + mesmo local, em área comum, várias vezes no período.

        Critério inicial (hipótese a validar com síndicos): 3 chamados em 90 dias.
        Convivência e problemas dentro da unidade não entram.
        """
        desde = timezone.now() - timedelta(days=dias)
        grupos = (
            self.chamados.filter(data_abertura__gte=desde)
            .exclude(status="cancelado")
            .exclude(tipo="barulho")
            .exclude(local="unidade")
            .values("tipo", "local")
            .annotate(total=Count("id"))
            .filter(total__gte=minimo)
            .order_by("-total")
        )
        tipos, locais = dict(Chamado.TIPOS), dict(Chamado.LOCAIS)
        return [
            {**g, "tipo_rotulo": tipos[g["tipo"]], "local_rotulo": locais[g["local"]], "dias": dias}
            for g in grupos
        ]


class Unidade(models.Model):
    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, related_name="unidades")
    identificador = models.CharField("identificador", max_length=30)

    class Meta:
        ordering = ["id"]
        verbose_name = "unidade"
        verbose_name_plural = "unidades"
        constraints = [
            models.UniqueConstraint(
                fields=["condominio", "identificador"], name="unidade_unica_por_condominio"
            )
        ]

    def __str__(self):
        return self.identificador

    @property
    def em_uso(self):
        return self.chamados.exists() or self.moradores.exists() or self.chamados_envolvida.exists()


class Perfil(models.Model):
    """Liga um usuário a um condomínio, com o papel dele (síndico ou morador)."""

    SINDICO = "sindico"
    MORADOR = "morador"
    PAPEIS = [(SINDICO, "Síndico"), (MORADOR, "Morador")]

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil")
    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, related_name="perfis")
    unidade = models.ForeignKey(
        Unidade, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="moradores", verbose_name="unidade",
    )
    papel = models.CharField("perfil", max_length=10, choices=PAPEIS, default=MORADOR)
    telefone = models.CharField("telefone", max_length=20, blank=True)
    aprovado = models.BooleanField("aprovado pelo síndico", default=False)
    criado_em = models.DateTimeField("cadastrado em", auto_now_add=True)

    class Meta:
        ordering = ["usuario__first_name"]
        verbose_name = "perfil"
        verbose_name_plural = "perfis"

    def __str__(self):
        return f"{self.nome} ({self.get_papel_display()})"

    @property
    def nome(self):
        return self.usuario.get_full_name() or self.usuario.email

    @property
    def eh_sindico(self):
        return self.papel == self.SINDICO


class Chamado(models.Model):
    TIPOS = [
        ("eletrica", "Elétrica"),
        ("hidraulica", "Hidráulica"),
        ("estrutura", "Estrutura e conservação"),
        ("limpeza", "Limpeza"),
        ("seguranca", "Segurança"),
        ("barulho", "Barulho e convivência"),
        ("outro", "Outro"),
    ]
    LOCAIS = [
        ("unidade", "Dentro da unidade"),
        ("garagem", "Garagem"),
        ("elevador", "Elevador"),
        ("corredor", "Escadas e corredores"),
        ("portaria", "Portaria e entrada"),
        ("lazer", "Área de lazer"),
        ("externa", "Jardim e área externa"),
        ("fachada", "Fachada e telhado"),
        ("outro", "Outro local"),
    ]
    URGENCIAS = [
        ("baixa", "Baixa"),
        ("media", "Média"),
        ("alta", "Alta"),
    ]
    STATUS = [
        ("aberto", "Aberto"),
        ("andamento", "Em andamento"),
        ("concluido", "Concluído"),
        ("cancelado", "Cancelado"),
    ]
    # Rito justo para conflitos: aviso → notificação → defesa → decisão.
    ETAPAS = [
        ("", "Sem rito"),
        ("aviso", "Aviso amigável"),
        ("notificacao", "Notificação formal"),
        ("defesa", "Defesa apresentada"),
        ("decisao", "Decisão"),
    ]
    RESULTADOS = [
        ("", "—"),
        ("arquivado", "Resolvido / arquivado"),
        ("advertencia", "Advertência"),
        ("multa", "Multa"),
    ]

    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, related_name="chamados")
    unidades = models.ManyToManyField(Unidade, verbose_name="unidades solicitantes", related_name="chamados")
    tipo = models.CharField("tipo de registro", max_length=20, choices=TIPOS)
    local = models.CharField("local", max_length=20, choices=LOCAIS, default="unidade")
    urgencia = models.CharField("nível de urgência", max_length=10, choices=URGENCIAS, default="media")
    status = models.CharField("status", max_length=10, choices=STATUS, default="aberto")
    solicitante_nome = models.CharField("nome completo do solicitante", max_length=150)
    descricao = models.TextField("descrição", blank=True)
    data_abertura = models.DateTimeField("data de abertura", auto_now_add=True)

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="chamados_criados", verbose_name="registrado por",
    )
    privado = models.BooleanField(
        "privado", default=False,
        help_text="Só o síndico e a sua unidade veem. Recomendado para barulho e convivência.",
    )
    unidade_envolvida = models.ForeignKey(
        Unidade, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="chamados_envolvida", verbose_name="unidade envolvida",
        help_text="Ex.: de onde vem o barulho. Ela não vê quem registrou.",
    )
    afetados = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="chamados_afetado",
        verbose_name="também afetados",
    )
    etapa = models.CharField("etapa do rito", max_length=12, choices=ETAPAS, blank=True, default="")
    resultado = models.CharField("resultado", max_length=12, choices=RESULTADOS, blank=True, default="")

    class Meta:
        ordering = ["-data_abertura"]
        verbose_name = "chamado"
        verbose_name_plural = "chamados"

    def __str__(self):
        return f"#{self.pk} {self.get_tipo_display()} — {self.condominio}"

    @property
    def encerrado(self):
        return self.status in ("concluido", "cancelado")

    @property
    def registrado_pelo_sindico(self):
        perfil = getattr(self.criado_por, "perfil", None)
        return bool(perfil and perfil.eh_sindico and self.solicitante_nome != perfil.nome)

    # ---------- Regras de acesso ----------

    @classmethod
    def visiveis_para(cls, perfil):
        """Chamados que o usuário pode ver. Ninguém vê outro condomínio."""
        qs = cls.objects.filter(condominio=perfil.condominio)
        if perfil.eh_sindico:
            return qs
        filtro = Q(privado=False) | Q(criado_por=perfil.usuario) | Q(afetados=perfil.usuario)
        if perfil.unidade_id:
            filtro |= Q(unidades=perfil.unidade_id)
            # A unidade envolvida passa a ver o caso a partir do aviso (sem saber quem registrou).
            filtro |= Q(unidade_envolvida=perfil.unidade_id) & ~Q(etapa="")
            # Antes do aviso, a unidade envolvida não vê a reclamação sobre ela.
            qs = qs.exclude(unidade_envolvida=perfil.unidade_id, etapa="")
        return qs.filter(filtro).distinct()

    def relacao(self, perfil):
        """Como o usuário se relaciona com o chamado: define o que ele vê e pode fazer."""
        if perfil.condominio_id != self.condominio_id:
            return None
        if perfil.eh_sindico:
            return "sindico"
        # .all() aproveita o prefetch_related da lista de chamados.
        if self.criado_por_id == perfil.usuario_id or (
            perfil.unidade_id and any(u.pk == perfil.unidade_id for u in self.unidades.all())
        ):
            return "solicitante"
        if perfil.unidade_id and self.unidade_envolvida_id == perfil.unidade_id:
            return "envolvido" if self.etapa else None
        if not self.privado or self.ja_afetado(perfil.usuario):
            return "vizinho"
        return None

    def ja_afetado(self, usuario):
        return any(u.pk == usuario.pk for u in self.afetados.all())


class Andamento(models.Model):
    """Histórico do chamado: cada mudança e cada etapa do rito fica registrada."""

    TIPOS = [
        ("abertura", "Abertura"),
        ("status", "Status"),
        ("urgencia", "Urgência"),
        ("edicao", "Edição"),
        ("afetado", "Também afetado"),
        ("aviso", "Aviso amigável"),
        ("notificacao", "Notificação formal"),
        ("defesa", "Defesa"),
        ("decisao", "Decisão"),
    ]
    # Quem vê cada tipo de registro, além do síndico.
    VISIVEL = {
        "solicitante": {"abertura", "status", "urgencia", "edicao", "afetado", "aviso", "notificacao", "decisao"},
        "envolvido": {"aviso", "notificacao", "defesa", "decisao"},
        "vizinho": {"abertura", "status", "afetado"},
    }

    chamado = models.ForeignKey(Chamado, on_delete=models.CASCADE, related_name="andamentos")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.CharField("tipo", max_length=12, choices=TIPOS)
    texto = models.TextField("texto", blank=True)
    data = models.DateTimeField("data", auto_now_add=True)

    class Meta:
        ordering = ["data", "id"]
        verbose_name = "andamento"
        verbose_name_plural = "andamentos"

    def __str__(self):
        return f"{self.get_tipo_display()} — chamado #{self.chamado_id}"

    @classmethod
    def visiveis(cls, chamado, relacao):
        qs = chamado.andamentos.select_related("autor__perfil")
        if relacao == "sindico":
            return qs
        return qs.filter(tipo__in=cls.VISIVEL.get(relacao, set()))
