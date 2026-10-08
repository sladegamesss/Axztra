"""
Correos automáticos (RF08, CU21 Notificar por correo).

Cada función arma un correo con su plantilla de templates/plataforma/correos/.
Los correos se envían después de confirmar la transacción y en segundo plano, para no demorar la página.
En desarrollo se muestran en la terminal; para enviarlos de verdad se configura EMAIL_HOST (ver README).
"""

import atexit
import logging
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger('plataforma.correo')

_ejecutor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='axztra-correo')
atexit.register(_ejecutor.shutdown, wait=True)


# Dirección completa para los enlaces de los correos.
def _url_absoluta(request, ruta):
    if request is None:
        return f"{settings.AXZTRA['URL_SITIO']}{ruta}"
    return request.build_absolute_uri(ruta)


# Indica si el correo se envía en segundo plano.
def _asincrono():
    backend = settings.EMAIL_BACKEND.lower()
    return settings.AXZTRA.get('CORREO_ASINCRONO', True) and 'locmem' not in backend and 'dummy' not in backend


# Envía el correo y registra cualquier error sin interrumpir al usuario.
def _entregar(asunto, cuerpo, destinatarios):
    try:
        send_mail(asunto, cuerpo, settings.DEFAULT_FROM_EMAIL, destinatarios, fail_silently=False)
        return True
    except Exception:
        logger.exception('No se pudo enviar el correo "%s"', asunto)
        return False


# Prepara el correo desde su plantilla y lo programa para después del commit.
def _enviar(asunto, plantilla, contexto, destinatarios, inmediato=False):
    from .models import ConfiguracionSitio

    destinatarios = sorted({correo for correo in destinatarios if correo and not correo.endswith('.invalid')})
    if not destinatarios:
        return False
    contexto = {**contexto, 'empresa': settings.AXZTRA, 'sitio': ConfiguracionSitio.actual()}
    cuerpo = render_to_string(plantilla, contexto)
    if inmediato or not _asincrono():
        return _entregar(asunto, cuerpo, destinatarios)
    _ejecutor.submit(_entregar, asunto, cuerpo, destinatarios)
    return True


# Destinatarios del equipo: el responsable o, si no hay, todo el equipo y el correo de administración.
def _correos_equipo(solicitud=None):
    if solicitud is not None and solicitud.responsable_id and solicitud.responsable.is_active and solicitud.responsable.email:
        return [solicitud.responsable.email]
    User = get_user_model()
    correos = set(
        User.objects.filter(is_staff=True, is_active=True)
        .exclude(email='')
        .values_list('email', flat=True)
    )
    correos.add(settings.AXZTRA['CORREO_ADMINISTRACION'])
    return sorted(correos)


# Respeta la preferencia del cliente de recibir avisos.
def _cliente_acepta(usuario):
    perfil = getattr(usuario, 'perfil_cliente', None)
    return usuario.is_active and (perfil is None or perfil.recibir_notificaciones)


# Confirmación al cliente y aviso al equipo cuando llega una solicitud nueva.
def solicitud_registrada(solicitud, request=None):
    if _cliente_acepta(solicitud.cliente):
        _enviar(
            f'Recibimos tu solicitud {solicitud.numero}',
            'plataforma/correos/solicitud_cliente.txt',
            {'solicitud': solicitud, 'url': _url_absoluta(request, solicitud.get_absolute_url())},
            [solicitud.cliente.email],
        )
    _enviar(
        f'Nueva solicitud {solicitud.numero} - {solicitud.get_tipo_display()}',
        'plataforma/correos/solicitud_admin.txt',
        {'solicitud': solicitud, 'url': _url_absoluta(request, reverse('panel_solicitud', args=[solicitud.pk]))},
        _correos_equipo(),
    )


# Aviso al cliente cuando cambia el estado de su solicitud.
def estado_actualizado(solicitud, comentario='', request=None):
    if not _cliente_acepta(solicitud.cliente):
        return
    _enviar(
        f'Tu solicitud {solicitud.numero} ahora está: {solicitud.estado.nombre}',
        'plataforma/correos/estado_cliente.txt',
        {'solicitud': solicitud, 'comentario': comentario, 'url': _url_absoluta(request, solicitud.get_absolute_url())},
        [solicitud.cliente.email],
    )


# Aviso al cliente cuando hay una cotización lista.
def cotizacion_emitida(solicitud, request=None):
    if not solicitud.cliente.is_active:
        return
    _enviar(
        f'Cotización disponible para {solicitud.numero}',
        'plataforma/correos/cotizacion_cliente.txt',
        {'solicitud': solicitud, 'cotizacion': solicitud.cotizacion, 'url': _url_absoluta(request, solicitud.get_absolute_url())},
        [solicitud.cliente.email],
    )


# Aviso al equipo cuando el cliente acepta o rechaza.
def cotizacion_respondida(solicitud, request=None):
    _enviar(
        f'El cliente respondió la cotización de {solicitud.numero}',
        'plataforma/correos/respuesta_admin.txt',
        {'solicitud': solicitud, 'cotizacion': solicitud.cotizacion, 'url': _url_absoluta(request, reverse('panel_solicitud', args=[solicitud.pk]))},
        _correos_equipo(solicitud),
    )


# Aviso al equipo cuando el cliente cancela.
def solicitud_cancelada(solicitud, request=None):
    _enviar(
        f'Solicitud {solicitud.numero} cancelada por el cliente',
        'plataforma/correos/cancelacion_admin.txt',
        {'solicitud': solicitud, 'url': _url_absoluta(request, reverse('panel_solicitud', args=[solicitud.pk]))},
        _correos_equipo(solicitud),
    )


# Aviso de mensaje nuevo a la otra parte de la conversación.
def mensaje_nuevo(mensaje, request=None):
    solicitud = mensaje.solicitud
    if mensaje.es_equipo:
        if not _cliente_acepta(solicitud.cliente):
            return
        _enviar(
            f'Tienes un mensaje nuevo sobre {solicitud.numero}',
            'plataforma/correos/mensaje_cliente.txt',
            {'solicitud': solicitud, 'mensaje': mensaje, 'url': _url_absoluta(request, solicitud.get_absolute_url() + '#mensajes')},
            [solicitud.cliente.email],
        )
    else:
        _enviar(
            f'Mensaje del cliente en {solicitud.numero}',
            'plataforma/correos/mensaje_equipo.txt',
            {'solicitud': solicitud, 'mensaje': mensaje, 'url': _url_absoluta(request, reverse('panel_solicitud', args=[solicitud.pk]) + '#mensajes')},
            _correos_equipo(solicitud),
        )


# Aviso al integrante del equipo que queda a cargo.
def responsable_asignado(solicitud, request=None):
    if not solicitud.responsable_id or not solicitud.responsable.email:
        return
    _enviar(
        f'Se te asignó la solicitud {solicitud.numero}',
        'plataforma/correos/asignacion_equipo.txt',
        {'solicitud': solicitud, 'url': _url_absoluta(request, reverse('panel_solicitud', args=[solicitud.pk]))},
        [solicitud.responsable.email],
    )


# Envía el código de 6 dígitos (CU07). Se manda de inmediato, no en segundo plano.
def codigo_verificacion(usuario, codigo):
    return _enviar(
        'Tu código de acceso a AXZTRA',
        'plataforma/correos/codigo_verificacion.txt',
        {'usuario': usuario, 'codigo': codigo, 'minutos': settings.AXZTRA['CODIGO_VERIFICACION_MINUTOS']},
        [usuario.email],
        inmediato=True,
    )


# Correo de bienvenida al registrarse.
def bienvenida(usuario, request=None):
    _enviar(
        'Bienvenido a AXZTRA',
        'plataforma/correos/bienvenida.txt',
        {'usuario': usuario, 'url': _url_absoluta(request, reverse('nueva_solicitud'))},
        [usuario.email],
    )
