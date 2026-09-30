import os
from pathlib import Path

from django.contrib.messages import constants as message_constants

BASE_DIR = Path(__file__).resolve().parent.parent


def _entorno_bool(nombre, defecto):
    valor = os.environ.get(nombre)
    if valor is None:
        return defecto
    return valor.strip().lower() in ('1', 'true', 'si', 'yes', 'on')


def _entorno_lista(nombre, defecto):
    valor = os.environ.get(nombre)
    if not valor:
        return defecto
    return [item.strip() for item in valor.split(',') if item.strip()]


SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'axztra-desarrollo-local-reemplazar-en-produccion-7f3c9a1e5b',
)

DEBUG = _entorno_bool('DJANGO_DEBUG', True)

ALLOWED_HOSTS = _entorno_lista('DJANGO_ALLOWED_HOSTS', ['localhost', '127.0.0.1', '[::1]'])

INSTALLED_APPS = [
    'plataforma.apps.AxztraAdminConfig',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'plataforma.apps.PlataformaConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'axztra.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'plataforma.context_processors.datos_empresa',
            ],
        },
    },
]

WSGI_APPLICATION = 'axztra.wsgi.application'

if os.environ.get('POSTGRES_DB'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('POSTGRES_DB'),
            'USER': os.environ.get('POSTGRES_USER', 'postgres'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
            'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'inicio'
LOGOUT_REDIRECT_URL = 'inicio'

SESSION_COOKIE_AGE = 60 * 60 * 8
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24

MESSAGE_TAGS = {
    message_constants.ERROR: 'danger',
}

EMAIL_BACKEND = os.environ.get('DJANGO_EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = _entorno_bool('EMAIL_USE_TLS', True)
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'AXZTRA <notificaciones@axztra.cl>')

AXZTRA = {
    'NOMBRE': 'AXZTRA',
    'CORREO_CONTACTO': os.environ.get('AXZTRA_CORREO', 'contacto@axztra.cl'),
    'CORREO_ADMINISTRACION': os.environ.get('AXZTRA_CORREO_ADMIN', 'contacto@axztra.cl'),
    'WHATSAPP': os.environ.get('AXZTRA_WHATSAPP', '56912345678'),
    'WHATSAPP_VISIBLE': os.environ.get('AXZTRA_WHATSAPP_VISIBLE', '+56 9 1234 5678'),
    'UBICACION': 'Hualpén, Región del Biobío, Chile',
    'CODIGO_VERIFICACION_MINUTOS': 10,
    'CODIGO_VERIFICACION_INTENTOS': 5,
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'consola': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'plataforma': {'handlers': ['consola'], 'level': 'INFO'},
    },
}

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
