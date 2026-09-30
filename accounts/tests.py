"""Testes automatizados principais do ClinSecure.

Execute com:
    python manage.py test accounts

Os testes cobrem os fluxos atualmente implementados em accounts/views.py,
permissions.py, models.py e crypto.py.
"""

import shutil
import tempfile
from datetime import timedelta, date
from io import BytesIO
from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django_otp.plugins.otp_totp.models import TOTPDevice

from .crypto import decrypt_data, decrypt_file, encrypt_data, encrypt_file
from .models import (
    Acesso,
    AuditLog,
    Consentimento,
    DadoPesquisa,
    Documento,
    ParticipacaoPesquisa,
    Participante,
    Pesquisa,
    Usuario,
)
from .permissions import (
    eh_admin_ou_coordenador,
    usuario_pode_acessar_documento,
    usuario_pode_acessar_participante,
    usuario_pode_acessar_pesquisa,
)


TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="clinsecure-tests-")


@override_settings(
    FIELD_ENCRYPTION_KEY=Fernet.generate_key(),
    MEDIA_ROOT=TEST_MEDIA_ROOT,
)
class ClinSecureBaseTest(TestCase):
    PASSWORD = "SenhaForte123!"

    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_user(
            username="admin_teste",
            email="admin@teste.local",
            password=cls.PASSWORD,
            perfil="administrador",
        )
        cls.coordenador = Usuario.objects.create_user(
            username="coord_teste",
            email="coord@teste.local",
            password=cls.PASSWORD,
            perfil="coordenador",
        )
        cls.responsavel_a = Usuario.objects.create_user(
            username="resp_a",
            email="resp.a@teste.local",
            password=cls.PASSWORD,
            perfil="responsavel",
        )
        cls.responsavel_b = Usuario.objects.create_user(
            username="resp_b",
            email="resp.b@teste.local",
            password=cls.PASSWORD,
            perfil="responsavel",
        )
        cls.pesquisador_a = Usuario.objects.create_user(
            username="pesq_a",
            email="pesq.a@teste.local",
            password=cls.PASSWORD,
            perfil="pesquisador",
        )
        cls.pesquisador_b = Usuario.objects.create_user(
            username="pesq_b",
            email="pesq.b@teste.local",
            password=cls.PASSWORD,
            perfil="pesquisador",
        )
        cls.participante_user_a = Usuario.objects.create_user(
            username="part_a",
            email="part.a@teste.local",
            password=cls.PASSWORD,
            perfil="participante",
        )
        cls.participante_user_b = Usuario.objects.create_user(
            username="part_b",
            email="part.b@teste.local",
            password=cls.PASSWORD,
            perfil="participante",
        )

        cls.pesquisa_a = Pesquisa.objects.create(
            registro_pesquisa="PESQ-TEST-001",
            nome="Pesquisa A",
            descricao="Pesquisa de teste A",
            status="ativa",
            responsavel=cls.responsavel_a,
        )
        cls.pesquisa_b = Pesquisa.objects.create(
            registro_pesquisa="PESQ-TEST-002",
            nome="Pesquisa B",
            descricao="Pesquisa de teste B",
            status="ativa",
            responsavel=cls.responsavel_b,
        )

        cls.pesquisa_a.pesquisadores.add(cls.pesquisador_a)
        cls.pesquisa_b.pesquisadores.add(cls.pesquisador_b)

        cls.participante_a = Participante.objects.create(
            registro_participante="PT-TEST-0001",
            nome_encrypted=encrypt_data("Nome A"),
            cpf_encrypted=encrypt_data("11111111111"),
            data_nascimento_encrypted=encrypt_data("2000-01-01"),
            usuario=cls.participante_user_a,
        )
        cls.participante_b = Participante.objects.create(
            registro_participante="PT-TEST-0002",
            nome_encrypted=encrypt_data("Nome B"),
            cpf_encrypted=encrypt_data("22222222222"),
            data_nascimento_encrypted=encrypt_data("1990-02-02"),
            usuario=cls.participante_user_b,
        )

        cls.participacao_a = ParticipacaoPesquisa.objects.create(
            participante=cls.participante_a,
            pesquisa=cls.pesquisa_a,
            status="ativo",
        )
        cls.participacao_b = ParticipacaoPesquisa.objects.create(
            participante=cls.participante_b,
            pesquisa=cls.pesquisa_b,
            status="ativo",
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def login_as(self, usuario):
        self.client.force_login(usuario)

    def make_document(self):
        documento = Documento(
            participante=self.participante_a,
            responsavel=self.responsavel_a,
            nome_original="documento.pdf",
            status="pendente",
        )
        documento.arquivo_criptografado = ContentFile(
            b"conteudo-cifrado-de-teste",
            name="documento.pdf",
        )
        documento.save()
        return documento


class AuthenticationTests(ClinSecureBaseTest):
    @patch("accounts.views.time.sleep")
    def test_login_incorreto_incrementa_tentativa_e_registra_log(self, _):
        response = self.client.post(
            reverse("login"),
            {
                "username": self.responsavel_a.email,
                "password": "SenhaErrada123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.responsavel_a.refresh_from_db()
        self.assertEqual(self.responsavel_a.tentativas_login, 1)
        self.assertTrue(
            AuditLog.objects.filter(
                usuario=self.responsavel_a,
                evento="Login",
                resultado="Falha",
            ).exists()
        )

    @patch("accounts.views.time.sleep")
    def test_login_bloqueia_apos_cinco_tentativas(self, _):
        for _ in range(5):
            self.client.post(
                reverse("login"),
                {
                    "username": self.responsavel_a.email,
                    "password": "SenhaErrada123!",
                },
            )

        self.responsavel_a.refresh_from_db()
        self.assertEqual(self.responsavel_a.tentativas_login, 5)
        self.assertIsNotNone(self.responsavel_a.bloqueado_ate)
        self.assertGreater(self.responsavel_a.bloqueado_ate, timezone.now())
        self.assertTrue(
            AuditLog.objects.filter(
                usuario=self.responsavel_a,
                evento="Bloqueio de conta",
                resultado="Bloqueado",
            ).exists()
        )

    def test_login_durante_bloqueio_e_negado(self):
        self.responsavel_a.tentativas_login = 5
        self.responsavel_a.bloqueado_ate = timezone.now() + timedelta(minutes=5)
        self.responsavel_a.save(update_fields=["tentativas_login", "bloqueado_ate"])

        response = self.client.post(
            reverse("login"),
            {
                "username": self.responsavel_a.email,
                "password": self.PASSWORD,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            AuditLog.objects.filter(
                usuario=self.responsavel_a,
                evento="Tentativa durante bloqueio",
                resultado="Bloqueado",
            ).exists()
        )

    def test_login_correto_exige_2fa_ou_setup(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": self.responsavel_a.email,
                "password": self.PASSWORD,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            response["Location"],
            {reverse("setup_2fa"), reverse("verificar_2fa")},
        )
        self.assertEqual(
            self.client.session["pre_otp_user_id"],
            self.responsavel_a.id,
        )

    def test_login_por_email_e_case_insensitive(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": self.responsavel_a.email.upper(),
                "password": self.PASSWORD,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            response["Location"],
            {reverse("setup_2fa"), reverse("verificar_2fa")},
        )

    def test_logout_invalida_sessao(self):
        self.login_as(self.responsavel_a)
        response = self.client.get(reverse("logout"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class TwoFactorTests(ClinSecureBaseTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.device = TOTPDevice.objects.create(
            user=cls.responsavel_a,
            name="Celular Principal",
            confirmed=True,
        )

    def start_pre_otp_session(self):
        session = self.client.session
        session["pre_otp_user_id"] = self.responsavel_a.id
        session.save()

    @patch("accounts.views.TOTPDevice.verify_token", return_value=True)
    def test_2fa_correto_conclui_login(self, _):
        self.start_pre_otp_session()

        response = self.client.post(
            reverse("verificar_2fa"),
            {"token": "123456"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("home"))
        self.assertIn("_auth_user_id", self.client.session)
        self.assertNotIn("pre_otp_user_id", self.client.session)

    @patch("accounts.views.TOTPDevice.verify_token", return_value=False)
    @patch("accounts.views.time.sleep")
    def test_2fa_incorreto_incrementa_tentativa_e_registra_log(self, _, __):
        self.start_pre_otp_session()

        response = self.client.post(
            reverse("verificar_2fa"),
            {"token": "000000"},
        )

        self.assertEqual(response.status_code, 200)
        self.responsavel_a.refresh_from_db()
        self.assertEqual(self.responsavel_a.tentativas_2fa, 1)
        self.assertTrue(
            AuditLog.objects.filter(
                usuario=self.responsavel_a,
                evento="2FA",
                resultado="Falha",
            ).exists()
        )

    @patch("accounts.views.TOTPDevice.verify_token", return_value=False)
    @patch("accounts.views.time.sleep")
    def test_2fa_bloqueia_apos_cinco_tentativas(self, _, __):
        self.start_pre_otp_session()

        for _ in range(5):
            self.client.post(
                reverse("verificar_2fa"),
                {"token": "000000"},
            )

        self.responsavel_a.refresh_from_db()
        self.assertEqual(self.responsavel_a.tentativas_2fa, 5)
        self.assertIsNotNone(self.responsavel_a.bloqueado_2fa_ate)
        self.assertGreater(
            self.responsavel_a.bloqueado_2fa_ate,
            timezone.now(),
        )
        self.assertTrue(
            AuditLog.objects.filter(
                usuario=self.responsavel_a,
                evento="Bloqueio 2FA",
                resultado="Bloqueado",
            ).exists()
        )


class PasswordRecoveryTests(ClinSecureBaseTest):
    @patch("accounts.views.requests.post")
    def test_solicitacao_de_recuperacao_envia_brevo_e_registra_log(self, mock_post):
        mock_post.return_value = MagicMock()
        mock_post.return_value.raise_for_status.return_value = None

        response = self.client.post(
            reverse("password_reset"),
            {"identificador": self.responsavel_a.email},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("password_reset_done"))
        mock_post.assert_called_once()
        self.assertTrue(
            AuditLog.objects.filter(
                usuario=self.responsavel_a,
                evento="Solicitação de recuperação de senha",
                resultado="Sucesso",
            ).exists()
        )

    def test_token_invalido_e_rejeitado(self):
        token = default_token_generator.make_token(self.responsavel_a)
        uid = urlsafe_base64_encode(force_bytes(self.responsavel_a.pk))

        self.responsavel_a.set_password("OutraSenha123!")
        self.responsavel_a.save()

        response = self.client.get(
            reverse(
                "password_reset_confirm",
                kwargs={"uidb64": uid, "token": token},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["validlink"])
        self.assertTrue(
            AuditLog.objects.filter(
                usuario=self.responsavel_a,
                evento="Recuperação com falha — token inválido/expirado",
                resultado="Falha",
            ).exists()
        )

    def test_recuperacao_valida_altera_senha_e_invalida_reuso(self):
        token = default_token_generator.make_token(self.responsavel_a)
        uid = urlsafe_base64_encode(force_bytes(self.responsavel_a.pk))

        response = self.client.post(
            reverse(
                "password_reset_confirm",
                kwargs={"uidb64": uid, "token": token},
            ),
            {
                "new_password1": "NovaSenha123!",
                "new_password2": "NovaSenha123!",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("password_reset_complete"))

        self.responsavel_a.refresh_from_db()
        self.assertTrue(self.responsavel_a.check_password("NovaSenha123!"))

        reuso = self.client.get(
            reverse(
                "password_reset_confirm",
                kwargs={"uidb64": uid, "token": token},
            )
        )

        self.assertEqual(reuso.status_code, 200)
        self.assertFalse(reuso.context["validlink"])


class PermissionTests(ClinSecureBaseTest):
    def test_admin_e_coordenador_acessam_pesquisa(self):
        self.assertTrue(eh_admin_ou_coordenador(self.admin))
        self.assertTrue(eh_admin_ou_coordenador(self.coordenador))
        self.assertTrue(usuario_pode_acessar_pesquisa(self.admin, self.pesquisa_b))
        self.assertTrue(usuario_pode_acessar_pesquisa(self.coordenador, self.pesquisa_b))

    def test_responsavel_so_acessa_proprias_pesquisas(self):
        self.assertTrue(usuario_pode_acessar_pesquisa(self.responsavel_a, self.pesquisa_a))
        self.assertFalse(usuario_pode_acessar_pesquisa(self.responsavel_a, self.pesquisa_b))

    def test_pesquisador_so_acessa_pesquisas_vinculadas(self):
        self.assertTrue(usuario_pode_acessar_pesquisa(self.pesquisador_a, self.pesquisa_a))
        self.assertFalse(usuario_pode_acessar_pesquisa(self.pesquisador_a, self.pesquisa_b))

    def test_participante_so_acessa_propria_pesquisa(self):
        self.assertTrue(usuario_pode_acessar_pesquisa(self.participante_user_a, self.pesquisa_a))
        self.assertFalse(usuario_pode_acessar_pesquisa(self.participante_user_a, self.pesquisa_b))

    def test_participante_so_acessa_proprio_registro(self):
        self.assertTrue(usuario_pode_acessar_participante(self.participante_user_a, self.participante_a))
        self.assertFalse(usuario_pode_acessar_participante(self.participante_user_a, self.participante_b))

    def test_pesquisador_so_acessa_participante_de_pesquisa_vinculada(self):
        self.assertTrue(usuario_pode_acessar_participante(self.pesquisador_a, self.participante_a))
        self.assertFalse(usuario_pode_acessar_participante(self.pesquisador_a, self.participante_b))

    def test_participante_so_acessa_documento_proprio(self):
        documento = self.make_document()
        self.assertTrue(usuario_pode_acessar_documento(self.participante_user_a, documento))
        self.assertFalse(usuario_pode_acessar_documento(self.participante_user_b, documento))

    def test_documento_com_acesso_valido_e_acessivel(self):
        documento = self.make_document()
        Acesso.objects.create(
            documento=documento,
            usuario=self.pesquisador_b,
            concedido_por=self.coordenador,
            inicio_acesso=timezone.now() - timedelta(minutes=1),
            fim_acesso=timezone.now() + timedelta(minutes=1),
        )
        self.assertTrue(usuario_pode_acessar_documento(self.pesquisador_b, documento))

    def test_documento_expirado_e_negado(self):
        documento = self.make_document()
        Acesso.objects.create(
            documento=documento,
            usuario=self.pesquisador_b,
            concedido_por=self.coordenador,
            inicio_acesso=timezone.now() - timedelta(minutes=10),
            fim_acesso=timezone.now() - timedelta(minutes=1),
        )
        self.assertFalse(usuario_pode_acessar_documento(self.pesquisador_b, documento))


class RouteAuthorizationTests(ClinSecureBaseTest):
    def test_pesquisador_nao_acessa_pesquisa_de_outro(self):
        self.login_as(self.pesquisador_a)
        response = self.client.get(
            reverse("detalhe_pesquisa", kwargs={"pesquisa_id": self.pesquisa_b.id})
        )
        self.assertEqual(response.status_code, 403)

    def test_responsavel_nao_edita_pesquisa_de_outro(self):
        self.login_as(self.responsavel_a)
        response = self.client.get(
            reverse("editar_pesquisa", kwargs={"pesquisa_id": self.pesquisa_b.id})
        )
        self.assertEqual(response.status_code, 403)

    def test_participante_nao_acessa_outro_participante(self):
        self.login_as(self.participante_user_a)
        response = self.client.get(
            reverse(
                "detalhe_participante",
                kwargs={"participante_id": self.participante_b.id},
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_participante_nao_acessa_area_de_logs(self):
        self.login_as(self.participante_user_a)
        response = self.client.get(reverse("analise_logs"))
        self.assertEqual(response.status_code, 403)

    def test_coordenador_acessa_area_de_logs(self):
        self.login_as(self.coordenador)
        response = self.client.get(reverse("analise_logs"))
        self.assertEqual(response.status_code, 200)

    def test_nao_autenticado_e_redirecionado_para_login(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_pesquisador_nao_deve_listar_pesquisas_de_terceiros(self):
        """Este teste deve revelar a implementação atual da lista de pesquisas.

        A permission function restringe o acesso corretamente, mas a view de
        listagem atualmente usa Pesquisa.objects.all() para pesquisador.
        """
        self.login_as(self.pesquisador_a)
        response = self.client.get(reverse("lista_pesquisas"))
        self.assertEqual(response.status_code, 200)

        pesquisas = list(response.context["pesquisas"])
        self.assertIn(self.pesquisa_a, pesquisas)
        self.assertNotIn(self.pesquisa_b, pesquisas)


class UploadTests(ClinSecureBaseTest):
    def setUp(self):
        super().setUp()
        self.login_as(self.responsavel_a)

    @staticmethod
    def pdf_file(name="documento.pdf", data=b"%PDF-1.7\n%ClinSecure\n"):
        return SimpleUploadedFile(
            name,
            data,
            content_type="application/pdf",
        )

    def test_constante_max_pdf_size_existe_e_e_10_mb(self):
        from . import views

        self.assertTrue(
            hasattr(views, "MAX_PDF_SIZE"),
            "MAX_PDF_SIZE não está definida em accounts/views.py.",
        )
        self.assertEqual(views.MAX_PDF_SIZE, 10 * 1024 * 1024)

    def test_upload_nao_pdf_e_rejeitado(self):
        arquivo = SimpleUploadedFile(
            "script.sh",
            b"#!/bin/bash\necho teste",
            content_type="application/x-sh",
        )

        response = self.client.post(
            reverse("upload_documento"),
            {
                "participante": self.participante_a.id,
                "arquivo": arquivo,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response,"Apenas arquivos PDF são permitidos.",status_code=400,)
        self.assertEqual(Documento.objects.count(), 0)

    def test_upload_script_renomeado_para_pdf_e_rejeitado(self):
        # Patch apenas a constante ausente para isolar a regra de Magic Bytes.
        # O teste acima continua denunciando a ausência real da constante.
        with patch("accounts.views.MAX_PDF_SIZE", 10 * 1024 * 1024, create=True):
            arquivo = self.pdf_file(
                name="script.pdf",
                data=b"#!/bin/bash\necho teste",
            )
            response = self.client.post(
                reverse("upload_documento"),
                {
                    "participante": self.participante_a.id,
                    "arquivo": arquivo,
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response,"O arquivo enviado não é um PDF válido.",status_code=400,)
        self.assertEqual(Documento.objects.count(), 0)

    def test_pdf_maior_que_10_mb_e_rejeitado(self):
        with patch("accounts.views.MAX_PDF_SIZE", 10 * 1024 * 1024, create=True):
            arquivo = self.pdf_file(
                data=b"%PDF-" + b"A" * (10 * 1024 * 1024 + 1)
            )
            response = self.client.post(
                reverse("upload_documento"),
                {
                    "participante": self.participante_a.id,
                    "arquivo": arquivo,
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response,"O arquivo PDF deve ter no máximo 10 MB.",status_code=400,)
        self.assertEqual(Documento.objects.count(), 0)

    @patch(
        "accounts.views.encrypt_file",
        return_value=ContentFile(b"arquivo-cifrado", name="documento.pdf"),
    )
    def test_pdf_valido_cria_documento_e_auditlog(self, mock_encrypt):
        with patch("accounts.views.MAX_PDF_SIZE", 10 * 1024 * 1024, create=True):
            response = self.client.post(
                reverse("upload_documento"),
                {
                    "participante": self.participante_a.id,
                    "arquivo": self.pdf_file(),
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Documento.objects.filter(
                participante=self.participante_a,
                nome_original="documento.pdf",
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                usuario=self.responsavel_a,
                evento="Upload de documento",
                resultado="Sucesso",
            ).exists()
        )
        mock_encrypt.assert_called_once()

    def test_responsavel_nao_envia_documento_de_participante_de_outro(self):
        with patch("accounts.views.MAX_PDF_SIZE", 10 * 1024 * 1024, create=True):
            response = self.client.post(
                reverse("upload_documento"),
                {
                    "participante": self.participante_b.id,
                    "arquivo": self.pdf_file(),
                },
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Documento.objects.count(), 0)

    def test_participante_nao_pode_fazer_upload(self):
        self.client.logout()
        self.login_as(self.participante_user_a)
        response = self.client.get(reverse("upload_documento"))
        self.assertEqual(response.status_code, 403)


class DocumentTests(ClinSecureBaseTest):
    def test_usuario_sem_acesso_nao_baixa_documento(self):
        documento = self.make_document()
        self.login_as(self.pesquisador_b)
        response = self.client.get(
            reverse("download_documento", kwargs={"documento_id": documento.id})
        )
        self.assertEqual(response.status_code, 403)

    def test_usuario_sem_acesso_nao_visualiza_documento(self):
        documento = self.make_document()
        self.login_as(self.pesquisador_b)
        response = self.client.get(
            reverse("visualizar_documento", kwargs={"documento_id": documento.id})
        )
        self.assertEqual(response.status_code, 403)

    @patch(
        "accounts.views.decrypt_file",
        return_value=BytesIO(b"%PDF-1.7\nconteudo"),
    )
    def test_participante_pode_visualizar_proprio_documento(self, mock_decrypt):
        documento = self.make_document()
        self.login_as(self.participante_user_a)

        response = self.client.get(
            reverse("visualizar_documento", kwargs={"documento_id": documento.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("inline;", response["Content-Disposition"])
        mock_decrypt.assert_called_once()

    @patch(
        "accounts.views.decrypt_file",
        return_value=BytesIO(b"conteudo"),
    )
    def test_participante_pode_baixar_proprio_documento(self, mock_decrypt):
        documento = self.make_document()
        self.login_as(self.participante_user_a)

        response = self.client.get(
            reverse("download_documento", kwargs={"documento_id": documento.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/octet-stream")
        self.assertIn("attachment;", response["Content-Disposition"])
        mock_decrypt.assert_called_once()

    def test_somente_coordenador_pode_conceder_acesso(self):
        documento = self.make_document()

        self.login_as(self.responsavel_a)
        response = self.client.post(
            reverse("conceder_acesso_documento", kwargs={"documento_id": documento.id}),
            {
                "usuario_id": self.pesquisador_b.id,
                "inicio_acesso": "2030-01-01T00:00",
                "fim_acesso": "2030-01-02T00:00",
            },
        )
        self.assertEqual(response.status_code, 403)

        self.client.logout()
        self.login_as(self.coordenador)
        response = self.client.post(
            reverse("conceder_acesso_documento", kwargs={"documento_id": documento.id}),
            {
                "usuario_id": self.pesquisador_b.id,
                "inicio_acesso": "2030-01-01T00:00",
                "fim_acesso": "2030-01-02T00:00",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Acesso.objects.filter(
                documento=documento,
                usuario=self.pesquisador_b,
                revogado=False,
            ).exists()
        )

    def test_coordenador_nao_cria_acesso_com_intervalo_invalido(self):
        documento = self.make_document()
        self.login_as(self.coordenador)
        response = self.client.post(
            reverse("conceder_acesso_documento", kwargs={"documento_id": documento.id}),
            {
                "usuario_id": self.pesquisador_b.id,
                "inicio_acesso": "2030-01-02T00:00",
                "fim_acesso": "2030-01-01T00:00",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            Acesso.objects.filter(
                documento=documento,
                usuario=self.pesquisador_b,
            ).exists()
        )

    def test_responsavel_pode_revogar_acesso_do_proprio_documento(self):
        documento = self.make_document()
        acesso = Acesso.objects.create(
            documento=documento,
            usuario=self.pesquisador_b,
            concedido_por=self.coordenador,
            inicio_acesso=timezone.now() - timedelta(minutes=1),
            fim_acesso=timezone.now() + timedelta(minutes=5),
        )

        self.login_as(self.responsavel_a)
        response = self.client.post(
            reverse("revogar_acesso_documento", kwargs={"acesso_id": acesso.id})
        )

        self.assertEqual(response.status_code, 200)
        acesso.refresh_from_db()
        self.assertTrue(acesso.revogado)
        self.assertIsNotNone(acesso.data_revogado)


@override_settings(FIELD_ENCRYPTION_KEY=Fernet.generate_key())
class CryptoTests(TestCase):
    def test_encrypt_e_decrypt_data(self):
        original = "João da Silva"
        encrypted = encrypt_data(original)
        self.assertNotEqual(encrypted, original)
        self.assertEqual(decrypt_data(encrypted), original)

    def test_encrypt_e_decrypt_file(self):
        original = b"%PDF-1.7\nClinSecure"
        source = SimpleUploadedFile(
            "teste.pdf",
            original,
            content_type="application/pdf",
        )
        encrypted = encrypt_file(source)
        self.assertNotEqual(encrypted.read(), original)
        encrypted.seek(0)
        decrypted = decrypt_file(encrypted)
        self.assertEqual(decrypted.getvalue(), original)


class LGPDTests(ClinSecureBaseTest):
    def test_participante_pode_acessar_meus_dados(self):
        self.login_as(self.participante_user_a)
        response = self.client.get(reverse("meus_dados"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["participante"], self.participante_a)
        self.assertEqual(response.context["nome"], "Nome A")

    def test_usuario_nao_participante_nao_acessa_meus_dados(self):
        self.login_as(self.responsavel_a)
        response = self.client.get(reverse("meus_dados"))
        self.assertEqual(response.status_code, 403)

    def test_consentimento_exige_aceite_explicito(self):
        self.login_as(self.participante_user_a)
        response = self.client.post(
            reverse("consentir_dados"),
            {"consentimento": "nao"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            Consentimento.objects.filter(
                participante=self.participante_a,
            ).exists()
        )

    def test_consentimento_e_registrado(self):
        self.login_as(self.participante_user_a)
        response = self.client.post(
            reverse("consentir_dados"),
            {"consentimento": "sim"},
        )

        self.assertEqual(response.status_code, 302)
        consentimento = Consentimento.objects.get(
            participante=self.participante_a,
            revogado=False,
        )
        self.assertEqual(consentimento.versao, "1.0")
        self.assertTrue(
            AuditLog.objects.filter(
                usuario=self.participante_user_a,
                evento="Consentimento registrado",
                resultado="Sucesso",
            ).exists()
        )

    def test_participante_nao_revoga_consentimento_de_outro(self):
        consentimento_b = Consentimento.objects.create(
            participante=self.participante_b,
            registrado_por=self.participante_user_b,
            finalidade="Gerenciamento e participação em pesquisas clínicas.",
            versao="1.0",
        )

        self.login_as(self.participante_user_a)
        response = self.client.post(
            reverse(
                "revogar_consentimento",
                kwargs={"consentimento_id": consentimento_b.id},
            )
        )

        self.assertEqual(response.status_code, 404)
        consentimento_b.refresh_from_db()
        self.assertFalse(consentimento_b.revogado)

    def test_revogacao_de_consentimento(self):
        consentimento = Consentimento.objects.create(
            participante=self.participante_a,
            registrado_por=self.participante_user_a,
            finalidade="Gerenciamento e participação em pesquisas clínicas.",
            versao="1.0",
        )

        self.login_as(self.participante_user_a)
        response = self.client.post(
            reverse(
                "revogar_consentimento",
                kwargs={"consentimento_id": consentimento.id},
            )
        )

        self.assertEqual(response.status_code, 302)
        consentimento.refresh_from_db()
        self.assertTrue(consentimento.revogado)
        self.assertIsNotNone(consentimento.data_revogado)

    @patch("accounts.views.decrypt_data")
    def test_exportacao_dos_dados_do_titular(self, mock_decrypt):
        mock_decrypt.side_effect = [
            "Nome A",
            "11111111111",
            "2000-01-01",
        ]

        self.login_as(self.participante_user_a)
        response = self.client.get(reverse("exportar_dados"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json; charset=utf-8")
        self.assertIn("meus_dados_clinsecure.json", response["Content-Disposition"])

        payload = response.json()
        self.assertEqual(payload["dados_pessoais"]["nome"], "Nome A")
        self.assertEqual(payload["dados_pessoais"]["cpf"], "11111111111")
        self.assertEqual(
            payload["dados_pessoais"]["registro_participante"],
            "PT-TEST-0001",
        )

    def test_exclusao_anonimiza_e_desativa_conta(self):
        self.login_as(self.participante_user_a)
        response = self.client.post(reverse("excluir_dados"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("login"))

        self.participante_a.refresh_from_db()
        self.participante_user_a.refresh_from_db()

        self.assertFalse(self.participante_a.ativo)
        self.assertEqual(decrypt_data(self.participante_a.nome_encrypted), "DADO_REMOVIDO")
        self.assertEqual(decrypt_data(self.participante_a.cpf_encrypted), "DADO_REMOVIDO")
        self.assertEqual(
            decrypt_data(self.participante_a.data_nascimento_encrypted),
            "DADO_REMOVIDO",
        )
        self.assertFalse(self.participante_user_a.is_active)
        self.assertEqual(self.participante_user_a.email, "")
        self.assertFalse(self.participante_user_a.has_usable_password())
        self.assertTrue(self.participante_user_a.username.startswith("anonimizado_"))
        self.assertTrue(
            AuditLog.objects.filter(
                usuario__isnull=True,
                evento="Exclusão de dados pessoais",
                resultado="Sucesso",
            ).exists()
        )


class ResearchDataTests(ClinSecureBaseTest):
    def test_dado_de_pesquisa_sem_consentimento_e_bloqueado(self):
        self.login_as(self.pesquisador_a)
        response = self.client.post(
            reverse(
                "cadastrar_dado_pesquisa",
                kwargs={"participacao_id": self.participacao_a.id},
            ),
            {
                "tipo": "Exame",
                "data_coleta": "2026-09-18",
                "resultado": "Normal",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            DadoPesquisa.objects.filter(
                participacao=self.participacao_a,
            ).exists()
        )

    def test_dado_de_pesquisa_com_consentimento_e_criado_e_criptografado(self):
        Consentimento.objects.create(
            participante=self.participante_a,
            registrado_por=self.participante_user_a,
            finalidade="Gerenciamento e participação em pesquisas clínicas.",
            versao="1.0",
        )

        self.login_as(self.pesquisador_a)
        response = self.client.post(
            reverse(
                "cadastrar_dado_pesquisa",
                kwargs={"participacao_id": self.participacao_a.id},
            ),
            {
                "tipo": "Exame",
                "data_coleta": "2026-09-18",
                "resultado": "Normal",
            },
        )

        self.assertEqual(response.status_code, 302)
        dado = DadoPesquisa.objects.get(participacao=self.participacao_a)
        self.assertEqual(decrypt_data(dado.resultado_encrypted), "Normal")
        self.assertTrue(
            AuditLog.objects.filter(
                usuario=self.pesquisador_a,
                evento="Cadastro de dado de pesquisa",
                resultado="Sucesso",
            ).exists()
        )

    def test_pesquisador_nao_cadastra_dado_em_pesquisa_de_outro(self):
        self.login_as(self.pesquisador_a)
        response = self.client.post(
            reverse(
                "cadastrar_dado_pesquisa",
                kwargs={"participacao_id": self.participacao_b.id},
            ),
            {
                "tipo": "Exame",
                "data_coleta": "2026-09-18",
                "resultado": "Normal",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            DadoPesquisa.objects.filter(
                participacao=self.participacao_b,
            ).exists()
        )


class AuditLogTests(ClinSecureBaseTest):
    def test_auditlog_pode_ser_criado(self):
        log = AuditLog.objects.create(
            usuario=self.admin,
            evento="Teste",
            ip="127.0.0.1",
            resultado="Sucesso",
            detalhes="Registro de teste",
        )
        self.assertIsNotNone(log.pk)

    def test_auditlog_existente_nao_pode_ser_alterado(self):
        log = AuditLog.objects.create(
            usuario=self.admin,
            evento="Teste",
            ip="127.0.0.1",
            resultado="Sucesso",
            detalhes="Original",
        )
        log.detalhes = "Alterado"

        with self.assertRaises(ValueError):
            log.save()

    def test_auditlog_nao_pode_ser_excluido(self):
        log = AuditLog.objects.create(
            usuario=self.admin,
            evento="Teste",
            ip="127.0.0.1",
            resultado="Sucesso",
            detalhes="Original",
        )

        with self.assertRaises(ValueError):
            log.delete()

    def test_painel_de_logs_e_restrito(self):
        self.login_as(self.pesquisador_a)
        response = self.client.get(reverse("analise_logs"))
        self.assertEqual(response.status_code, 403)

        self.client.logout()
        self.login_as(self.coordenador)
        response = self.client.get(reverse("analise_logs"))
        self.assertEqual(response.status_code, 200)
