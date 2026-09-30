import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger('plataforma')


def _url_absoluta(request, ruta):
    if request is None:
        return ruta
    return request.build_absolute_uri(ruta)


def _enviar(asunto, plantilla, contexto, destinatarios):
    destinatarios = [correo for correo in destinatarios if correo]
    if not destinatarios:
        return False
    contexto = {**contexto, 'empresa': settings.AXZTRA}
    cuerpo = render_to_string(plantilla, contexto)
    try:
        send_mail(asunto, cuerpo, settings.DEFAULT_FROM_EMAIL, destinatarios, fail_silently=False)
        return True
    except Exception:
        logger.exception('No se pudo enviar el correo "%s"', asunto)
        return False


def _correos_administracion():
    User = get_user_model()
    correos = set(
        User.objects.filter(is_staff=True, is_active=True)
        .exclude(email='')
        .values_list('email', flat=True)
    )
    correos.add(settings.AXZTRA['CORREO_ADMINISTRACION'])
    return sorted(correos)


def _cliente_acepta(usuario):
    perfil = getattr(usuario, 'perfil_cliente', None)
    return perfil is None or perfil.recibir_notificaciones


def solicitud_registrada(solicitud, request=None):
    url_cliente = _url_absoluta(request, solicitud.get_absolute_url())
    url_panel = _url_absoluta(request, reverse('panel_solicitud', args=[solicitud.pk]))
    contexto = {'solicitud': solicitud, 'url': url_cliente}
    if _cliente_acepta(solicitud.cliente):
        _enviar(
            f'Recibimos tu solicitud {solicitud.numero}',
            'plataforma/correos/solicitud_cliente.txt',
            contexto,
            [solicitud.cliente.email],
        )
    _enviar(
        f'Nueva solicitud {solicitud.numero} · {solicitud.get_tipo_display()}',
        'plataforma/correos/solicitud_admin.txt',
        {'solicitud': solicitud, 'url': url_panel},
        _correos_administracion(),
    )


def estado_actualizado(solicitud, comentario='', request=None):
    if not _cliente_acepta(solicitud.cliente):
        return
    _enviar(
        f'Tu solicitud {solicitud.numero} ahora está: {solicitud.estado.nombre}',
        'plataforma/correos/estado_cliente.txt',
        {'solicitud': solicitud, 'comentario': comentario, 'url': _url_absoluta(request, solicitud.get_absolute_url())},
        [solicitud.cliente.email],
    )


def cotizacion_emitida(solicitud, request=None):
    _enviar(
        f'Cotización disponible para {solicitud.numero}',
        'plataforma/correos/cotizacion_cliente.txt',
        {'solicitud': solicitud, 'cotizacion': solicitud.cotizacion, 'url': _url_absoluta(request, solicitud.get_absolute_url())},
        [solicitud.cliente.email],
    )


def cotizacion_respondida(solicitud, request=None):
    _enviar(
        f'El cliente respondió la cotización de {solicitud.numero}',
        'plataforma/correos/respuesta_admin.txt',
        {'solicitud': solicitud, 'cotizacion': solicitud.cotizacion, 'url': _url_absoluta(request, reverse('panel_solicitud', args=[solicitud.pk]))},
        _correos_administracion(),
    )


def solicitud_cancelada(solicitud, request=None):
    _enviar(
        f'Solicitud {solicitud.numero} cancelada por el cliente',
        'plataforma/correos/cancelacion_admin.txt',
        {'solicitud': solicitud, 'url': _url_absoluta(request, reverse('panel_solicitud', args=[solicitud.pk]))},
        _correos_administracion(),
    )


def codigo_verificacion(usuario, codigo):
    return _enviar(
        'Tu código de acceso al panel AXZTRA',
        'plataforma/correos/codigo_verificacion.txt',
        {'usuario': usuario, 'codigo': codigo, 'minutos': settings.AXZTRA['CODIGO_VERIFICACION_MINUTOS']},
        [usuario.email],
    )


def bienvenida(usuario, request=None):
    _enviar(
        'Bienvenido a AXZTRA',
        'plataforma/correos/bienvenida.txt',
        {'usuario': usuario, 'url': _url_absoluta(request, reverse('nueva_solicitud'))},
        [usuario.email],
    )
