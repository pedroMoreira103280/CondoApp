"""Login e perfis (síndico/morador), convite, histórico, privacidade, rito e "também afetado"."""

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import core.models


def preencher_convites(apps, schema_editor):
    # Um código diferente para cada condomínio já existente.
    Condominio = apps.get_model("core", "Condominio")
    for condominio in Condominio.objects.all():
        condominio.codigo_convite = core.models.gerar_codigo_convite()
        condominio.save(update_fields=["codigo_convite"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # O síndico agora é um usuário com login (Perfil), não mais campos de texto.
        migrations.RemoveField(model_name="condominio", name="sindico_nome"),
        migrations.RemoveField(model_name="condominio", name="sindico_telefone"),
        migrations.RemoveField(model_name="condominio", name="sindico_email"),
        migrations.AddField(
            model_name="condominio",
            name="codigo_convite",
            field=models.CharField(max_length=20, null=True, verbose_name="código de convite"),
        ),
        migrations.RunPython(preencher_convites, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="condominio",
            name="codigo_convite",
            field=models.CharField(
                default=core.models.gerar_codigo_convite, max_length=20, unique=True, verbose_name="código de convite"
            ),
        ),
        migrations.AddField(
            model_name="condominio",
            name="criado_em",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name="criado em"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="chamado",
            name="local",
            field=models.CharField(
                choices=[
                    ("unidade", "Dentro da unidade"), ("garagem", "Garagem"), ("elevador", "Elevador"),
                    ("corredor", "Escadas e corredores"), ("portaria", "Portaria e entrada"), ("lazer", "Área de lazer"),
                    ("externa", "Jardim e área externa"), ("fachada", "Fachada e telhado"), ("outro", "Outro local"),
                ],
                default="unidade", max_length=20, verbose_name="local",
            ),
        ),
        migrations.AddField(
            model_name="chamado",
            name="criado_por",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="chamados_criados", to=settings.AUTH_USER_MODEL, verbose_name="registrado por",
            ),
        ),
        migrations.AddField(
            model_name="chamado",
            name="privado",
            field=models.BooleanField(
                default=False, verbose_name="privado",
                help_text="Só o síndico e a sua unidade veem. Recomendado para barulho e convivência.",
            ),
        ),
        migrations.AddField(
            model_name="chamado",
            name="unidade_envolvida",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="chamados_envolvida", to="core.unidade", verbose_name="unidade envolvida",
                help_text="Ex.: de onde vem o barulho. Ela não vê quem registrou.",
            ),
        ),
        migrations.AddField(
            model_name="chamado",
            name="afetados",
            field=models.ManyToManyField(
                blank=True, related_name="chamados_afetado", to=settings.AUTH_USER_MODEL, verbose_name="também afetados"
            ),
        ),
        migrations.AddField(
            model_name="chamado",
            name="etapa",
            field=models.CharField(
                blank=True, default="", max_length=12, verbose_name="etapa do rito",
                choices=[
                    ("", "Sem rito"), ("aviso", "Aviso amigável"), ("notificacao", "Notificação formal"),
                    ("defesa", "Defesa apresentada"), ("decisao", "Decisão"),
                ],
            ),
        ),
        migrations.AddField(
            model_name="chamado",
            name="resultado",
            field=models.CharField(
                blank=True, default="", max_length=12, verbose_name="resultado",
                choices=[("", "—"), ("arquivado", "Resolvido / arquivado"), ("advertencia", "Advertência"), ("multa", "Multa")],
            ),
        ),
        migrations.CreateModel(
            name="Perfil",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("papel", models.CharField(choices=[("sindico", "Síndico"), ("morador", "Morador")], default="morador", max_length=10, verbose_name="perfil")),
                ("telefone", models.CharField(blank=True, max_length=20, verbose_name="telefone")),
                ("aprovado", models.BooleanField(default=False, verbose_name="aprovado pelo síndico")),
                ("criado_em", models.DateTimeField(auto_now_add=True, verbose_name="cadastrado em")),
                ("condominio", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="perfis", to="core.condominio")),
                ("unidade", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="moradores", to="core.unidade", verbose_name="unidade")),
                ("usuario", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="perfil", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "perfil", "verbose_name_plural": "perfis", "ordering": ["usuario__first_name"]},
        ),
        migrations.CreateModel(
            name="Andamento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(
                    choices=[
                        ("abertura", "Abertura"), ("status", "Status"), ("urgencia", "Urgência"), ("edicao", "Edição"),
                        ("afetado", "Também afetado"), ("aviso", "Aviso amigável"), ("notificacao", "Notificação formal"),
                        ("defesa", "Defesa"), ("decisao", "Decisão"),
                    ],
                    max_length=12, verbose_name="tipo",
                )),
                ("texto", models.TextField(blank=True, verbose_name="texto")),
                ("data", models.DateTimeField(auto_now_add=True, verbose_name="data")),
                ("autor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("chamado", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="andamentos", to="core.chamado")),
            ],
            options={"verbose_name": "andamento", "verbose_name_plural": "andamentos", "ordering": ["data", "id"]},
        ),
    ]
