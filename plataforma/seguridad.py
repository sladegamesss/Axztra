"""
Seguridad general del sitio.

Cabeceras de seguridad (incluida la política de contenido CSP) y límites de peticiones
para evitar abusos en registro, inicio de sesión, mensajes, archivos, asistente y API.
"""

import logging
from functools import wraps
from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render

logger = logging.getLogger('plataforma.seguridad')

FUENTES_BASE = {
    'default-src': ["'self'"],
    'script-src': ["'self'"],
    'style-src': ["'self'", "'unsafe-inline'", 'https://fonts.googleapis.com'],
    'font-src': ["'self'", 'https://fonts.gstatic.com', 'data:'],
    'img-src': ["'self'", 'data:'],
    'connect-src': ["'self'"],
    'frame-src': ["'none'"],
    'object-src': ["'none'"],
    'base-uri': ["'self'"],
    'form-action': ["'self'"],
    'frame-ancestors': ["'none'"],
}


# Dominios de Botpress que se permiten si está configurado.
def _origenes_botpress():
    origenes = set()
    for url in settings.AXZTRA.get('BOTPRESS_SCRIPTS', []):
        partes = urlparse(url)
        if partes.scheme == 'https' and partes.netloc:
            origenes.add(f'https://{partes.netloc}')
    if origenes:
        origenes.update({'https://*.botpress.cloud', 'https://*.bpcontent.cloud'})
    return sorted(origenes)


# Arma la política CSP: solo se cargan scripts y estilos del propio sitio y fuentes permitidas.
def politica_contenido():
    fuentes = {clave: list(valores) for clave, valores in FUENTES_BASE.items()}
    externos = _origenes_botpress()
    if externos:
        for directiva in ('script-src', 'style-src', 'img-src', 'font-src', 'connect-src'):
            fuentes[directiva].extend(externos)
        fuentes['connect-src'].append('wss://*.botpress.cloud')
        fuentes['frame-src'] = externos
    return '; '.join(f"{directiva} {' '.join(valores)}" for directiva, valores in fuentes.items())


# Agrega las cabeceras de seguridad a todas las respuestas.
class CabecerasSeguridadMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.politica = politica_contenido()

    def __call__(self, request):
        respuesta = self.get_response(request)
        respuesta.headers.setdefault('Content-Security-Policy', self.politica)
        respuesta.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=(), payment=(), usb=()')
        respuesta.headers.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        if request.path.startswith(('/cuenta/', '/panel/', '/solicitudes/', f'/{settings.ADMIN_URL}')):
            respuesta.headers.setdefault('Cache-Control', 'no-store, private')
        return respuesta


# Dirección IP del visitante (considera el proxy si está configurado).
def ip_cliente(request):
    if settings.AXZTRA.get('CONFIAR_PROXY'):
        reenviada = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if reenviada:
            return reenviada.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or '0.0.0.0'


# Clave de caché para contar intentos.
def _clave(nombre):
    return f'axztra:limite:{nombre}'


# Suma un intento dentro de una ventana de tiempo.
def contar(nombre, ventana):
    clave = _clave(nombre)
    if cache.add(clave, 1, ventana):
        return 1
    try:
        return cache.incr(clave)
    except ValueError:
        cache.set(clave, 1, ventana)
        return 1


# Cantidad de intentos registrados.
def valor(nombre):
    return cache.get(_clave(nombre), 0)


# Borra el contador (por ejemplo, tras un ingreso correcto).
def reiniciar(nombre):
    cache.delete(_clave(nombre))


# Permite desactivar los límites con AXZTRA_LIMITES_ACTIVOS=0.
def limites_activos():
    return settings.AXZTRA.get('LIMITES_ACTIVOS', True)


# Indica si se superó el máximo permitido.
def excede(nombre, limite, ventana):
    if not limites_activos():
        return False
    return contar(nombre, ventana) > limite


# Indica si un correo o IP está bloqueado temporalmente.
def bloqueado(nombre, limite):
    if not limites_activos():
        return False
    return valor(nombre) >= limite


# Respuesta 429 (demasiadas peticiones) en HTML o JSON.
def respuesta_limite(request, como_json=False):
    mensaje = 'Recibimos demasiadas solicitudes seguidas. Espera unos minutos e inténtalo nuevamente.'
    logger.warning('Límite de solicitudes alcanzado en %s desde %s', request.path, ip_cliente(request))
    if como_json:
        return JsonResponse({'error': mensaje}, status=429)
    return render(request, 'plataforma/error.html', {
        'codigo': 429,
        'titulo': 'Demasiadas solicitudes',
        'mensaje': mensaje,
    }, status=429)


# Decorador para limitar cuántas veces se puede usar una vista, por IP o por usuario.
def limitar(prefijo, limite, ventana, como_json=False, por_usuario=False):
    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
                if por_usuario and request.user.is_authenticated:
                    identidad = f'u{request.user.pk}'
                else:
                    identidad = ip_cliente(request)
                if excede(f'{prefijo}:{identidad}', limite, ventana):
                    return respuesta_limite(request, como_json)
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador
