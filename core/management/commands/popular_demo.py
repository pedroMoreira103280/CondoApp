"""Cria um condomínio de demonstração com síndico, moradores e chamados.

Uso:  python manage.py popular_demo
      python manage.py popular_demo --recriar   (apaga e cria de novo)
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Andamento, Chamado, Condominio, Perfil

NOME = "Residencial Bela Vista (demonstração)"
SENHA = "Condo@2026"  # senha de teste de todas as contas da demonstração

CONTAS = [
    # e-mail, nome, papel, unidade, aprovado
    ("sindico@example.com", "Marta Ribeiro", Perfil.SINDICO, "Bloco A - 101", True),
    ("morador1@example.com", "Carlos Souza", Perfil.MORADOR, "Bloco A - 102", True),
    ("morador2@example.com", "Juliana Prado", Perfil.MORADOR, "Bloco A - 201", True),
    ("morador3@example.com", "Rafael Lima", Perfil.MORADOR, "Bloco A - 202", True),
    ("pendente@example.com", "Beatriz Nunes", Perfil.MORADOR, "Bloco B - 101", False),
]


class Command(BaseCommand):
    help = "Cria um condomínio de demonstração (contas de teste com a senha Condo@2026)."

    def add_arguments(self, parser):
        parser.add_argument("--recriar", action="store_true", help="Apaga a demonstração anterior e cria de novo.")

    @transaction.atomic
    def handle(self, *args, recriar=False, **options):
        User = get_user_model()
        emails = [c[0] for c in CONTAS]
        if Condominio.objects.filter(nome=NOME).exists() or User.objects.filter(username__in=emails).exists():
            if not recriar:
                self.stdout.write(self.style.WARNING("A demonstração já existe. Use --recriar para apagar e criar de novo."))
                return
            Condominio.objects.filter(nome=NOME).delete()
            User.objects.filter(username__in=emails).delete()

        c = Condominio.objects.create(nome=NOME, endereco="Rua das Araucárias, 500, Água Verde, Curitiba", numero_unidades=8)
        nomes = [f"Bloco {b} - {a}{n:02d}" for b in "AB" for a in (1, 2) for n in (1, 2)]
        for unidade, nome in zip(c.unidades.all(), nomes):
            unidade.identificador = nome
            unidade.save()
        u = {x.identificador: x for x in c.unidades.all()}

        usuarios = {}
        for email, nome, papel, unidade, aprovado in CONTAS:
            primeiro, _, resto = nome.partition(" ")
            user = User.objects.create_user(username=email, email=email, password=SENHA, first_name=primeiro, last_name=resto)
            Perfil.objects.create(usuario=user, condominio=c, papel=papel, unidade=u[unidade], aprovado=aprovado, telefone="(41) 99999-0000")
            usuarios[email] = user
        sindico, m1, m2, m3 = (usuarios[e] for e in emails[:4])

        def chamado(autor, unidades, **campos):
            ch = Chamado.objects.create(condominio=c, criado_por=autor, solicitante_nome=campos.pop("nome", autor.get_full_name()), **campos)
            ch.unidades.set([u[x] for x in unidades])
            Andamento.objects.create(chamado=ch, autor=autor, tipo="abertura")
            return ch

        # Reincidência: 3 vazamentos na garagem geram sugestão de preventiva.
        for autor, unidade, texto in [
            (m1, "Bloco A - 102", "Goteira perto da vaga 12."),
            (m2, "Bloco A - 201", "Poça d'água na rampa da garagem."),
            (m3, "Bloco A - 202", "Infiltração no teto da garagem, perto do portão."),
        ]:
            chamado(autor, [unidade], tipo="hidraulica", local="garagem", urgencia="media", descricao=texto)

        # "Também estou afetado": um chamado público com dois vizinhos somados.
        elevador = chamado(m1, ["Bloco A - 102"], tipo="eletrica", local="elevador", urgencia="alta",
                           descricao="Luz do elevador piscando e botão do 2º andar sem funcionar.")
        for vizinho in (m2, m3):
            elevador.afetados.add(vizinho)
            Andamento.objects.create(chamado=elevador, autor=vizinho, tipo="afetado", texto=f"Unidade {vizinho.perfil.unidade} também está afetada.")

        # Privacidade e rito: barulho, privado, já na etapa de notificação.
        barulho = chamado(m2, ["Bloco A - 201"], tipo="barulho", local="unidade", urgencia="media", privado=True,
                          unidade_envolvida=u["Bloco A - 202"], descricao="Som alto depois das 23h, três noites seguidas.")
        Andamento.objects.create(chamado=barulho, autor=sindico, tipo="aviso", texto="Lembramos que o regimento prevê silêncio das 22h às 7h. Contamos com a sua colaboração.")
        Andamento.objects.create(chamado=barulho, autor=sindico, tipo="notificacao", texto="O barulho após as 22h voltou a ser registrado. Você pode apresentar defesa em até 5 dias.")
        barulho.etapa, barulho.status = "notificacao", "andamento"
        barulho.save()

        # Modo híbrido: síndico registra por uma moradora que não usa o app.
        chamado(sindico, ["Bloco B - 102"], nome="Dona Ivone (Bloco B - 102)", tipo="estrutura", local="corredor",
                urgencia="baixa", descricao="Corrimão da escada solto entre o 1º e o 2º andar. Avisou na portaria.")

        self.stdout.write(self.style.SUCCESS(f"Demonstração criada: {NOME}"))
        self.stdout.write(f"Senha de todas as contas: {SENHA}")
        for email, nome, papel, unidade, aprovado in CONTAS:
            self.stdout.write(f"  {email:24} {nome:15} {papel:8} {unidade}{'' if aprovado else '  (aguardando aprovação)'}")
