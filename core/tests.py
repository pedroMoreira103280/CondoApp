"""Testes das regras de acesso, privacidade e rito.  Rodar:  python manage.py test"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Andamento, Chamado, Condominio, Perfil

User = get_user_model()
SENHA = "Teste@2026"


def criar_conta(condominio, email, papel=Perfil.MORADOR, unidade=None, aprovado=True):
    user = User.objects.create_user(username=email, email=email, password=SENHA, first_name=email.split("@")[0].title())
    Perfil.objects.create(usuario=user, condominio=condominio, papel=papel, unidade=unidade, aprovado=aprovado)
    return user


class Base(TestCase):
    def setUp(self):
        self.c = Condominio.objects.create(nome="Alfa", endereco="Rua A", numero_unidades=4)
        self.u1, self.u2, self.u3, self.u4 = self.c.unidades.all()
        self.sindico = criar_conta(self.c, "sindico@a.com", Perfil.SINDICO)
        self.ana = criar_conta(self.c, "ana@a.com", unidade=self.u1)
        self.bia = criar_conta(self.c, "bia@a.com", unidade=self.u2)
        self.caio = criar_conta(self.c, "caio@a.com", unidade=self.u3)

        self.outro = Condominio.objects.create(nome="Beta", endereco="Rua B", numero_unidades=2)
        self.de_fora = criar_conta(self.outro, "fora@b.com", unidade=self.outro.unidades.first())

    def entrar(self, user):
        self.client.force_login(user)

    def novo_chamado(self, autor, unidade, **campos):
        ch = Chamado.objects.create(condominio=self.c, criado_por=autor, solicitante_nome=autor.first_name, tipo=campos.pop("tipo", "hidraulica"), **campos)
        ch.unidades.set([unidade])
        return ch


class LoginECadastroTests(Base):
    def test_telas_internas_exigem_login(self):
        for nome in ["chamado_lista", "chamado_novo", "meu_perfil", "moradores", "condominio"]:
            resposta = self.client.get(reverse(nome))
            self.assertRedirects(resposta, f"{reverse('entrar')}?next={reverse(nome)}", msg_prefix=nome)

    def test_login_com_email(self):
        resposta = self.client.post(reverse("entrar"), {"username": "ANA@a.com", "password": SENHA})
        self.assertRedirects(resposta, reverse("chamado_lista"))

    def test_cadastro_do_sindico_cria_condominio_e_unidades(self):
        resposta = self.client.post(reverse("cadastro_sindico"), {
            "condominio_nome": "Gama", "endereco": "Rua G", "numero_unidades": 12,
            "nome": "Sara Síndica", "email": "sara@g.com", "senha": "Gama@2026xy", "senha2": "Gama@2026xy",
        })
        self.assertRedirects(resposta, reverse("condominio"))
        perfil = User.objects.get(username="sara@g.com").perfil
        self.assertTrue(perfil.eh_sindico and perfil.aprovado)
        self.assertEqual(perfil.condominio.unidades.count(), 12)

    def test_morador_pelo_convite_fica_pendente_ate_aprovacao(self):
        url = reverse("convite", args=[self.c.codigo_convite])
        self.client.post(url, {"nome": "Davi", "unidade": self.u4.pk, "email": "davi@a.com", "senha": "Davi@2026xy", "senha2": "Davi@2026xy"})
        davi = User.objects.get(username="davi@a.com")
        self.assertFalse(davi.perfil.aprovado)
        resposta = self.client.post(reverse("entrar"), {"username": "davi@a.com", "password": "Davi@2026xy"})
        self.assertContains(resposta, "aguarda a aprovação")

        self.entrar(self.sindico)
        self.client.post(reverse("morador_aprovar", args=[davi.perfil.pk]))
        davi.perfil.refresh_from_db()
        self.assertTrue(davi.perfil.aprovado)

    def test_convite_antigo_para_de_funcionar(self):
        antigo = self.c.codigo_convite
        self.c.novo_convite()
        self.assertEqual(self.client.get(reverse("convite", args=[antigo])).status_code, 404)


class PermissoesTests(Base):
    def test_morador_nao_acessa_telas_do_sindico(self):
        self.entrar(self.ana)
        for nome in ["moradores", "condominio", "unidades", "convite_imprimir"]:
            self.assertEqual(self.client.get(reverse(nome)).status_code, 403, nome)
        ch = self.novo_chamado(self.ana, self.u1)
        self.assertEqual(self.client.get(reverse("chamado_editar", args=[ch.pk])).status_code, 403)

    def test_morador_nao_muda_status(self):
        ch = self.novo_chamado(self.ana, self.u1)
        self.entrar(self.ana)
        self.client.post(reverse("chamado_detalhe", args=[ch.pk]), {"status": "concluido", "urgencia": "alta"})
        ch.refresh_from_db()
        self.assertEqual(ch.status, "aberto")

    def test_ninguem_ve_outro_condominio(self):
        ch = self.novo_chamado(self.ana, self.u1)
        self.entrar(self.de_fora)
        self.assertEqual(self.client.get(reverse("chamado_detalhe", args=[ch.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("chamado_lista")), f"#{ch.pk}<")
        alvo = self.ana.perfil
        self.assertEqual(self.client.get(reverse("morador_editar", args=[alvo.pk])).status_code, 403)

    def test_sindico_nao_edita_usuario_de_outro_condominio(self):
        self.entrar(self.sindico)
        self.assertEqual(self.client.get(reverse("morador_editar", args=[self.de_fora.perfil.pk])).status_code, 404)

    def test_sindico_edita_morador_e_muda_unidade(self):
        self.entrar(self.sindico)
        p = self.bia.perfil
        self.client.post(reverse("morador_editar", args=[p.pk]), {
            "dados": "1", "nome": "Bia Nova", "email": "bia@a.com", "unidade": self.u4.pk, "papel": "morador", "ativo": "on",
        })
        p.refresh_from_db()
        self.assertEqual(p.unidade, self.u4)

    def test_sindico_nao_se_rebaixa(self):
        self.entrar(self.sindico)
        p = self.sindico.perfil
        self.client.post(reverse("morador_editar", args=[p.pk]), {"dados": "1", "nome": "S", "email": "sindico@a.com", "papel": "morador", "unidade": self.u1.pk})
        p.refresh_from_db()
        self.assertTrue(p.eh_sindico)

    def test_morador_so_abre_chamado_pela_propria_unidade(self):
        self.entrar(self.ana)
        self.client.post(reverse("chamado_novo"), {"tipo": "eletrica", "local": "garagem", "urgencia": "media", "unidades": [self.u2.pk]})
        ch = Chamado.objects.get()
        self.assertEqual(list(ch.unidades.all()), [self.u1])
        self.assertEqual(ch.criado_por, self.ana)

    def test_bloqueado_nao_entra(self):
        self.ana.is_active = False
        self.ana.save()
        resposta = self.client.post(reverse("entrar"), {"username": "ana@a.com", "password": SENHA})
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)


class PrivacidadeERitoTests(Base):
    def setUp(self):
        super().setUp()
        # Ana reclama de barulho da unidade do Caio, em privado.
        self.barulho = self.novo_chamado(self.ana, self.u1, tipo="barulho", privado=True, unidade_envolvida=self.u3, descricao="Som alto da Ana")

    def test_chamado_privado_some_para_vizinhos(self):
        self.entrar(self.bia)
        self.assertEqual(self.client.get(reverse("chamado_detalhe", args=[self.barulho.pk])).status_code, 404)

    def test_envolvido_so_ve_depois_do_aviso_e_sem_saber_quem_reclamou(self):
        self.entrar(self.caio)
        self.assertEqual(self.client.get(reverse("chamado_detalhe", args=[self.barulho.pk])).status_code, 404)

        self.entrar(self.sindico)
        self.client.post(reverse("chamado_etapa", args=[self.barulho.pk, "aviso"]), {"aviso-texto": "Lembrete do regimento."})

        self.entrar(self.caio)
        resposta = self.client.get(reverse("chamado_detalhe", args=[self.barulho.pk]))
        self.assertContains(resposta, "Lembrete do regimento.")
        self.assertNotContains(resposta, "Som alto da Ana")
        self.assertNotContains(resposta, "Ana")

    def test_multa_exige_notificacao_antes(self):
        self.entrar(self.sindico)
        self.client.post(reverse("chamado_etapa", args=[self.barulho.pk, "aviso"]), {"aviso-texto": "Aviso"})
        self.client.post(reverse("chamado_etapa", args=[self.barulho.pk, "decisao"]), {"decisao-texto": "Multa", "decisao-resultado": "multa"})
        self.barulho.refresh_from_db()
        self.assertEqual(self.barulho.etapa, "aviso")

        self.client.post(reverse("chamado_etapa", args=[self.barulho.pk, "notificacao"]), {"notificacao-texto": "Notificação"})
        self.entrar(self.caio)
        self.client.post(reverse("chamado_etapa", args=[self.barulho.pk, "defesa"]), {"defesa-texto": "Foi uma festa só."})
        self.entrar(self.sindico)
        self.client.post(reverse("chamado_etapa", args=[self.barulho.pk, "decisao"]), {"decisao-texto": "Advertência", "decisao-resultado": "advertencia"})
        self.barulho.refresh_from_db()
        self.assertEqual((self.barulho.etapa, self.barulho.status, self.barulho.resultado), ("decisao", "concluido", "advertencia"))
        self.assertTrue(Andamento.objects.filter(chamado=self.barulho, tipo="defesa").exists())

    def test_reclamante_nao_ve_a_defesa(self):
        Andamento.objects.create(chamado=self.barulho, autor=self.caio, tipo="defesa", texto="Minha defesa secreta")
        self.entrar(self.ana)
        self.assertNotContains(self.client.get(reverse("chamado_detalhe", args=[self.barulho.pk])), "Minha defesa secreta")


class OcorrenciasInteligentesTests(Base):
    def test_tambem_estou_afetado(self):
        ch = self.novo_chamado(self.ana, self.u1, local="garagem")
        self.entrar(self.bia)
        resposta = self.client.get(reverse("chamado_detalhe", args=[ch.pk]))
        self.assertContains(resposta, "Também estou afetado")
        self.assertNotContains(resposta, self.ana.first_name)  # vizinho não vê quem abriu
        self.client.post(reverse("chamado_afetado", args=[ch.pk]))
        self.assertTrue(ch.afetados.filter(pk=self.bia.pk).exists())

    def test_reincidencia_sugere_preventiva(self):
        for autor, unidade in [(self.ana, self.u1), (self.bia, self.u2), (self.caio, self.u3)]:
            self.novo_chamado(autor, unidade, local="garagem")
        sugestoes = self.c.sugestoes_preventiva()
        self.assertEqual(len(sugestoes), 1)
        self.assertEqual((sugestoes[0]["tipo"], sugestoes[0]["local"], sugestoes[0]["total"]), ("hidraulica", "garagem", 3))
        self.entrar(self.sindico)
        self.assertContains(self.client.get(reverse("chamado_lista")), "manutenção preventiva")
