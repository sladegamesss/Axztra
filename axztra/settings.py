"""
Configuración de Django para AXZTRA.

Todo lo que cambia entre desarrollo y producción se lee desde variables de entorno o desde el archivo .env.
La base de datos es PostgreSQL: los datos de conexión van en el archivo .env (hay un ejemplo en .env.example).
Los correos se muestran en la terminal mientras no se configure EMAIL_HOST.
La lista completa de variables está en el README (sección Configuración).
"""

import os
import sys
import dj_database_url
from pathlib import Path

from django.contrib.messages import constants as message_constants
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga el archivo .env de la raíz del proyecto (líneas CLAVE=valor). Una variable de entorno real tiene prioridad.
def cargar_env():
    ruta = BASE_DIR / '.env'
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding='utf-8-sig').splitlines():
        linea = linea.strip()
        if not linea or linea.startswith('#') or '=' not in linea:
            continue
        clave, valor = linea.split('=', 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))

cargar_env()

# Lee una variable de entorno como verdadero o falso (1/0, true/false).
def entorno_bool(nombre, defecto):
    valor = os.environ.get(nombre)
    if valor is None:
        return defecto
    return valor.strip().lower() in ('1', 'true', 'si', 'yes', 'on')

# Lee una variable de entorno separada por comas como lista.
def entorno_lista(nombre, defecto):
    valor = os.environ.get(nombre)
    if not valor:
        return defecto
    return [item.strip() for item in valor.split(',') if item.strip()]

# Lee una variable de entorno como número entero.
def entorno_int(nombre, defecto):
    try:
        return int(os.environ.get(nombre, defecto))
    except (TypeError, ValueError):
        return defecto

# Clave secreta. En producción es obligatorio definir DJANGO_SECRET_KEY.
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'axztra-desarrollo-local-reemplazar-en-produccion-7f3c9a1e5b',
)

DEBUG = entorno_bool('DJANGO_DEBUG', True)

if not DEBUG and SECRET_KEY.startswith('axztra-desarrollo-local'):
    raise ImproperlyConfigured('Define la variable de entorno DJANGO_SECRET_KEY antes de ejecutar con DJANGO_DEBUG=0.')

# PERMITIR CUALQUIER HOST (Necesario para Render)
ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = entorno_lista('DJANGO_CSRF_TRUSTED_ORIGINS', [])

# Aplicaciones instaladas. "plataforma" contiene todo el sistema AXZTRA.
INSTALLED_APPS = [
    'plataforma.apps.AxztraAdminConfig',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sitemaps',
    'anymail',
    'plataforma.apps.PlataformaConfig',
]

# Capas que procesan cada petición (seguridad, sesión, CSRF, autenticación, mensajes).
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'axztra.urls'

# Plantillas HTML. datos_empresa agrega la configuración del sitio a todas las páginas.
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
ASGI_APPLICATION = 'axztra.asgi.application'

# Base de datos PostgreSQL. 
# En la nube usa DATABASE_URL de Neon, en local usa los datos del .env
if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.config(conn_max_age=600, ssl_require=True)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('POSTGRES_DB', 'axztra'),
            'USER': os.environ.get('POSTGRES_USER', 'postgres'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
            'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        }
    }

if DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
    DATABASES['default']['CONN_MAX_AGE'] = entorno_int('DJANGO_CONN_MAX_AGE', 60)
    DATABASES['default']['CONN_HEALTH_CHECKS'] = True

# Caché: en memoria por defecto; Redis si se define REDIS_URL (necesario con varios procesos).
if os.environ.get('REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.environ['REDIS_URL'],
            'TIMEOUT': 300,
            'KEY_PREFIX': 'axztra',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'axztra',
            'TIMEOUT': 300,
            'OPTIONS': {'MAX_ENTRIES': 5000},
        }
    }

# Sesiones de 8 horas guardadas en la base de datos y en caché.
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_COOKIE_AGE = 60 * 60 * 8
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Reglas para las contraseñas.
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Idioma español de Chile y hora de Santiago.
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = False

# Archivos estáticos (CSS, JavaScript, imágenes) y archivos subidos por los usuarios (media).
STATIC_URL = '/static/'
STATIC_ROOT = Path(os.environ.get('DJANGO_STATIC_ROOT', BASE_DIR / 'staticfiles'))
MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.environ.get('DJANGO_MEDIA_ROOT', BASE_DIR / 'media'))

# Configuración estricta de WhiteNoise para producción
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

# Tamaños máximos de carga.
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
FILE_UPLOAD_PERMISSIONS = 0o640

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Páginas de inicio y cierre de sesión.
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'inicio'
LOGOUT_REDIRECT_URL = 'inicio'
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24

MESSAGE_TAGS = {
    message_constants.ERROR: 'danger',
}

# Correo: si no se define EMAIL_HOST, los correos se muestran en la terminal (útil para ver el código de verificación).
EMAIL_BACKEND = 'anymail.backends.brevo.EmailBackend'
ANYMAIL = {
    'BREVO_API_KEY': os.environ.get('BREVO_API_KEY', ''),
}
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'AXZTRA <benjamrui@gmail.com>')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Dirección de la administración de datos.
ADMIN_URL = os.environ.get('DJANGO_ADMIN_URL', 'admin/').strip('/') + '/'

# Parámetros propios de AXZTRA (nombre, correo de administración, Botpress, límites, etc.).
AXZTRA = {
    'NOMBRE': 'AXZTRA',
    'URL_SITIO': os.environ.get('AXZTRA_URL_SITIO', 'http://127.0.0.1:8000').rstrip('/'),
    'CORREO_CONTACTO': os.environ.get('AXZTRA_CORREO', 'contacto@axztra.cl'),
    'CORREO_ADMINISTRACION': os.environ.get('AXZTRA_CORREO_ADMIN', 'contacto@axztra.cl'),
    'WHATSAPP': os.environ.get('AXZTRA_WHATSAPP', '56912345678'),
    'WHATSAPP_VISIBLE': os.environ.get('AXZTRA_WHATSAPP_VISIBLE', '+56 9 1234 5678'),
    'UBICACION': 'Hualpén, Región del Biobío, Chile',
    'HORARIO': 'Lunes a viernes, de 9:00 a 18:00 horas',
    'CODIGO_VERIFICACION_MINUTOS': 10,
    'CODIGO_VERIFICACION_INTENTOS': 5,
    # Verificación en dos pasos también para los clientes. Con AXZTRA_VERIFICACION_CLIENTES=0 solo la usa el equipo.
    'VERIFICACION_CLIENTES': entorno_bool('AXZTRA_VERIFICACION_CLIENTES', True),
    'IVA': 19,
    'SLA_HORAS': {'urgente': 4, 'alta': 24, 'media': 48, 'baja': 72},
    'ADJUNTOS_MAXIMO_MB': 10,
    'ADJUNTOS_EXTENSIONES': ['pdf', 'png', 'jpg', 'jpeg', 'webp', 'gif', 'docx', 'xlsx', 'pptx', 'txt', 'zip'],
    'CORREO_ASINCRONO': entorno_bool('AXZTRA_CORREO_ASINCRONO', True),
    'CONFIAR_PROXY': entorno_bool('AXZTRA_CONFIAR_PROXY', False),
    'LIMITES_ACTIVOS': entorno_bool('AXZTRA_LIMITES_ACTIVOS', True),
    'BOTPRESS_SCRIPTS': entorno_lista('AXZTRA_BOTPRESS_SCRIPTS', []),
}

EN_PRUEBAS = len(sys.argv) > 1 and sys.argv[1] == 'test'

# Registro de eventos y errores en la terminal.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '[{asctime}] {levelname} {name}: {message}', 'style': '{', 'datefmt': '%d/%m/%Y %H:%M:%S'},
    },
    'handlers': {
        'consola': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'loggers': {
        'plataforma': {'handlers': ['consola'], 'level': 'CRITICAL' if EN_PRUEBAS else os.environ.get('AXZTRA_LOG_NIVEL', 'INFO'), 'propagate': False},
        'django.request': {'handlers': ['consola'], 'level': 'CRITICAL' if EN_PRUEBAS else 'ERROR', 'propagate': False},
        'django.security': {'handlers': ['consola'], 'level': 'WARNING', 'propagate': False},
    },
}

# Cabeceras de seguridad básicas.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'

# Ajustes que solo se aplican en producción (HTTPS, cookies seguras, HSTS).
if not DEBUG:
    SESSION_COOKIE_SECURE = entorno_bool('DJANGO_COOKIES_SEGURAS', True)
    CSRF_COOKIE_SECURE = entorno_bool('DJANGO_COOKIES_SEGURAS', True)
    SECURE_SSL_REDIRECT = entorno_bool('DJANGO_SSL_REDIRECT', False)
    SECURE_HSTS_SECONDS = entorno_int('DJANGO_HSTS_SEGUNDOS', 0)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
    SECURE_HSTS_PRELOAD = False
    if entorno_bool('DJANGO_DETRAS_DE_PROXY', False):
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')