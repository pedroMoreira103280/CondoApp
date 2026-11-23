"""Configurações do CondoApp (protótipo para rodar localmente)."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Chave só para desenvolvimento local. Em outro ambiente, defina DJANGO_SECRET_KEY.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-condoapp-somente-desenvolvimento")

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "condoapp.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.contexto.perfil",
            ],
        },
    },
]

WSGI_APPLICATION = "condoapp.wsgi.application"

# SQLite: um arquivo local, não precisa instalar nenhum banco.
# O arquivo db.sqlite3 só é criado quando você roda "python manage.py migrate".
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

# Login e sessão
LOGIN_URL = "entrar"
LOGIN_REDIRECT_URL = "chamado_lista"
LOGOUT_REDIRECT_URL = "entrar"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 14 dias
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"

# Mensagens de erro com estilo próprio (vermelho)
from django.contrib.messages import constants as mensagens  # noqa: E402
MESSAGE_TAGS = {mensagens.ERROR: "erro"}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
