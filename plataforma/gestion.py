from django.db import transaction
from django.utils import timezone

from . import notificaciones
from .estimacion import calcular_estimacion
from .models import Estimacion, EstadoSolicitud, HistorialSolicitud, RequerimientoWeb, Servicio, Solicitud


def registrar_historial(solicitud, estado_anterior, comentario='', usuario=None):
    return HistorialSolicitud.objects.create(
        solicitud=solicitud,
        estado_anterior=estado_anterior,
        estado_nuevo=solicitud.estado,
        comentario=comentario,
        usuario=usuario,
    )


@transaction.atomic
def crear_solicitud(cliente, tipo, datos, detalles=None, requerimiento=None, prioridad='media', request=None):
    solicitud = Solicitud.objects.create(
        cliente=cliente,
        tipo=tipo,
        servicio=datos.get('servicio'),
        titulo=datos['titulo'],
        descripcion=datos.get('descripcion') or 'Sin información adicional.',
        url_sitio=datos.get('url_sitio', ''),
        detalles=detalles or {},
        requerimiento=requerimiento,
        prioridad=prioridad,
        fecha_deseada=datos.get('fecha_deseada'),
    )
    registrar_historial(solicitud, None, 'Solicitud registrada por el cliente.', cliente)
    transaction.on_commit(lambda: notificaciones.solicitud_registrada(solicitud, request))
    return solicitud


@transaction.atomic
def crear_solicitud_web(cliente, datos, request=None):
    requerimiento = RequerimientoWeb.objects.create(
        nombre_negocio=datos['nombre_negocio'],
        rubro=datos['rubro'],
        descripcion_negocio=datos['descripcion_negocio'],
        publico_objetivo=datos.get('publico_objetivo', ''),
        tipo_sitio=datos['tipo_sitio'],
        tiene_sitio_actual=datos.get('tiene_sitio_actual') == 'si',
        url_sitio_actual=datos.get('url_sitio_actual', ''),
        objetivos=list(datos.get('objetivos', [])),
        num_paginas=datos['num_paginas'],
        complejidad=datos['complejidad'],
        funcionalidades=list(datos.get('funcionalidades', [])),
        integraciones=list(datos.get('integraciones', [])),
        tiene_contenido=datos.get('tiene_contenido', False),
        observaciones=datos.get('observaciones', ''),
    )
    resultado = calcular_estimacion(
        requerimiento.tipo_sitio,
        requerimiento.complejidad,
        requerimiento.num_paginas,
        requerimiento.funcionalidades,
        requerimiento.integraciones,
    )
    descripcion = datos['descripcion_negocio']
    if datos.get('observaciones'):
        descripcion = f"{descripcion}\n\nComentarios adicionales: {datos['observaciones']}"
    solicitud_datos = {
        'servicio': datos.get('servicio'),
        'titulo': datos['titulo'],
        'descripcion': descripcion,
        'url_sitio': requerimiento.url_sitio_actual,
        'fecha_deseada': datos.get('fecha_deseada'),
    }
    solicitud = crear_solicitud(cliente, Servicio.TIPO_CREACION, solicitud_datos, requerimiento=requerimiento, request=request)
    Estimacion.objects.create(
        solicitud=solicitud,
        total=resultado['total'],
        monto_minimo=resultado['monto_minimo'],
        monto_maximo=resultado['monto_maximo'],
        factor_complejidad=resultado['factor'],
        desglose=resultado['desglose'],
        semanas_minimas=resultado['semanas_minimas'],
        semanas_maximas=resultado['semanas_maximas'],
    )
    return solicitud


@transaction.atomic
def cambiar_estado(solicitud, nuevo_estado, usuario=None, comentario='', notificar=True, request=None):
    anterior = solicitud.estado
    if anterior.pk == nuevo_estado.pk:
        return None
    solicitud.estado = nuevo_estado
    solicitud.save(update_fields=['estado', 'fecha_actualizacion'])
    registro = registrar_historial(solicitud, anterior, comentario, usuario)
    if notificar:
        transaction.on_commit(lambda: notificaciones.estado_actualizado(solicitud, comentario, request))
    return registro


@transaction.atomic
def emitir_cotizacion(solicitud, formulario, usuario, request=None):
    cotizacion = formulario.save(commit=False)
    cotizacion.solicitud = solicitud
    cotizacion.emitida_por = usuario
    cotizacion.fecha_emision = timezone.now()
    cotizacion.respuesta_cliente = ''
    cotizacion.comentario_cliente = ''
    cotizacion.fecha_respuesta = None
    cotizacion.save()
    cotizada = EstadoSolicitud.obtener(EstadoSolicitud.COTIZADA)
    if solicitud.estado_id != cotizada.pk:
        cambiar_estado(solicitud, cotizada, usuario, 'Cotización formal emitida.', notificar=False)
    else:
        registrar_historial(solicitud, cotizada, 'Cotización formal actualizada.', usuario)
    transaction.on_commit(lambda: notificaciones.cotizacion_emitida(solicitud, request))
    return cotizacion


@transaction.atomic
def responder_cotizacion(solicitud, respuesta, comentario, usuario, request=None):
    cotizacion = solicitud.cotizacion
    cotizacion.respuesta_cliente = respuesta
    cotizacion.comentario_cliente = comentario
    cotizacion.fecha_respuesta = timezone.now()
    cotizacion.save(update_fields=['respuesta_cliente', 'comentario_cliente', 'fecha_respuesta'])
    codigo = EstadoSolicitud.APROBADA if respuesta == 'aceptada' else EstadoSolicitud.RECHAZADA
    texto = 'El cliente aceptó la cotización.' if respuesta == 'aceptada' else 'El cliente rechazó la cotización.'
    if comentario:
        texto = f'{texto} Comentario: {comentario}'
    cambiar_estado(solicitud, EstadoSolicitud.obtener(codigo), usuario, texto, notificar=False)
    transaction.on_commit(lambda: notificaciones.cotizacion_respondida(solicitud, request))


@transaction.atomic
def cancelar_solicitud(solicitud, usuario, request=None):
    cambiar_estado(solicitud, EstadoSolicitud.obtener(EstadoSolicitud.CANCELADA), usuario, 'Solicitud cancelada por el cliente.', notificar=False)
    transaction.on_commit(lambda: notificaciones.solicitud_cancelada(solicitud, request))
