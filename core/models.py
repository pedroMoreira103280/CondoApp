from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Condominio(models.Model):
    nome = models.CharField("nome", max_length=100)
    endereco = models.CharField("endereço", max_length=200)
    numero_unidades = models.PositiveIntegerField(
        "número de casas/apartamentos",
        validators=[MinValueValidator(1), MaxValueValidator(500)],
    )
    sindico_nome = models.CharField("nome do síndico", max_length=100)
    sindico_telefone = models.CharField("telefone do síndico", max_length=20, blank=True)
    sindico_email = models.EmailField("e-mail do síndico", blank=True)

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

    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, related_name="chamados")
    unidades = models.ManyToManyField(Unidade, verbose_name="unidades solicitantes", related_name="chamados")
    tipo = models.CharField("tipo de registro", max_length=20, choices=TIPOS)
    urgencia = models.CharField("nível de urgência", max_length=10, choices=URGENCIAS, default="media")
    status = models.CharField("status", max_length=10, choices=STATUS, default="aberto")
    solicitante_nome = models.CharField("nome completo do solicitante", max_length=150)
    descricao = models.TextField("descrição", blank=True)
    data_abertura = models.DateTimeField("data de abertura", auto_now_add=True)

    class Meta:
        ordering = ["-data_abertura"]
        verbose_name = "chamado"
        verbose_name_plural = "chamados"

    def __str__(self):
        return f"#{self.pk} {self.get_tipo_display()} — {self.condominio}"
