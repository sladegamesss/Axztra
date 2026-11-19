"""
Reglas de negocio de AXZTRA.

Las vistas no guardan datos directamente: llaman a estas funciones, que trabajan dentro de
transacciones y registran el historial y las notificaciones. Siguen los diagramas de actividades
DA-02 (solicitud de sitio web) y DA-03 (gestión y cotización) del informe.
"""

from django.db import IntegrityError, transaction
from django.utils import timezone

from . import auditoria, notificaciones
from .estimacion import calcular_estimacion
from .models import (
    Adjunto,
    Estimacion,
    EstadoSolicitud,
    HistorialSolicitud,
    MensajeSolicitud,
    RequerimientoWeb,
    Servicio,
    Solicitud,
)


# Se lanza cuando llega dos veces el mismo formulario (mismo token de envío).
class SolicitudDuplicada(Exception):
    def __init__(self, solicitud):
        super().__init__(solicitud.numero)
        self.solicitud = solicitud


# Busca si ya existe una solicitud de este cliente con el mismo token.
def buscar_por_token(cliente, token):
    if not token:
        return None
    return Solicitud.objects.filter(cliente=cliente, token_envio=token).first()


# Agrega un registro en plataforma_historialsolicitud.
def registrar_historial(solicitud, estado_anterior, comentario='', usuario=None):
    return HistorialSolicitud.objects.create(
        solicitud=solicitud,
        estado_anterior=estado_anterior,
        estado_nuevo=solicitud.estado,
        comentario=comentario,
        usuario=usuario,
    )


# CU08 Solicitar servicio: crea la solicitud en estado Recibida y avisa por correo (CU21).
@transaction.atomic
def crear_solicitud(cliente, tipo, datos, detalles=None, requerimiento=None, prioridad='media', request=None, token=None):
    existente = buscar_por_token(cliente, token)
    if existente is not None:
        raise SolicitudDuplicada(existente)
    campos = {
        'cliente': cliente,
        'tipo': tipo,
        'servicio': datos.get('servicio'),
        'titulo': datos['titulo'],
        'descripcion': datos.get('descripcion') or 'Sin información adicional.',
        'url_sitio': datos.get('url_sitio', ''),
        'detalles': detalles or {},
        'requerimiento': requerimiento,
        'prioridad': prioridad,
        'fecha_deseada': datos.get('fecha_deseada'),
        'relacionada': datos.get('relacionada'),
    }
    try:
        with transaction.atomic():
            solicitud = Solicitud.objects.create(token_envio=token, **campos)
    except IntegrityError:
        existente = buscar_por_token(cliente, token)
        if existente is not None:
            raise SolicitudDuplicada(existente)
        solicitud = Solicitud.objects.create(token_envio=None, **campos)
    registrar_historial(solicitud, None, 'Solicitud registrada por el cliente.', cliente)
    adjunto = datos.get('adjunto')
    if adjunto:
        guardar_adjunto(solicitud, adjunto, cliente, es_equipo=False)
    transaction.on_commit(lambda: notificaciones.solicitud_registrada(solicitud, request))
    return solicitud


# CU08 + CU09 + CU02: guarda el requerimiento web, calcula la estimación y crea la solicitud.
def crear_solicitud_web(cliente, datos, request=None, token=None):
    existente = buscar_por_token(cliente, token)
    if existente is not None:
        raise SolicitudDuplicada(existente)
    with transaction.atomic():
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
            estilo_visual=datos.get('estilo_visual') or 'sin_preferencia',
            colores=datos.get('colores', ''),
            secciones=list(datos.get('secciones', [])),
            situacion_logo=datos.get('situacion_logo') or 'tiene',
            tiene_contenido=datos.get('tiene_contenido', False),
            sitios_referencia=datos.get('sitios_referencia', ''),
            dominio=datos.get('dominio', ''),
            presupuesto=datos.get('presupuesto') or 'por_definir',
            medio_contacto=datos.get('medio_contacto') or 'correo',
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
        solicitud = crear_solicitud(
            cliente,
            Servicio.TIPO_CREACION,
            {
                'servicio': datos.get('servicio'),
                'titulo': datos['titulo'],
                'descripcion': descripcion,
                'url_sitio': requerimiento.url_sitio_actual,
                'fecha_deseada': datos.get('fecha_deseada'),
            },
            requerimiento=requerimiento,
            request=request,
            token=token,
        )
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


# CU17 Actualizar estado: valida la transición, guarda el historial y avisa al cliente.
@transaction.atomic
def cambiar_estado(solicitud, nuevo_estado, usuario=None, comentario='', notificar=True, request=None):
    anterior = solicitud.estado
    if anterior.pk == nuevo_estado.pk:
        return None
    solicitud.estado = nuevo_estado
    campos = ['estado', 'fecha_actualizacion']
    if solicitud.fecha_primera_respuesta is None and anterior.codigo == EstadoSolicitud.RECIBIDA and usuario is not None and usuario.is_staff:
        solicitud.fecha_primera_respuesta = timezone.now()
        campos.append('fecha_primera_respuesta')
    solicitud.save(update_fields=campos)
    registro = registrar_historial(solicitud, anterior, comentario, usuario)
    if usuario is not None and usuario.is_staff:
        auditoria.registrar(request, 'estado', f'{solicitud.numero}: {anterior.nombre} a {nuevo_estado.nombre}', solicitud, usuario)
    if notificar:
        transaction.on_commit(lambda: notificaciones.estado_actualizado(solicitud, comentario, request))
    return registro


# Reglas de qué estado puede seguir a cuál (ver diagrama de flujo, Figuras 6 y 7).
def validar_transicion(solicitud, nuevo_estado):
    if nuevo_estado.pk == solicitud.estado_id:
        return 'La solicitud ya se encuentra en ese estado.'
    if nuevo_estado.codigo == EstadoSolicitud.COTIZADA and not hasattr(solicitud, 'cotizacion'):
        return 'Primero emite la cotización definitiva.'
    return ''


# CU16 Emitir cotización definitiva: guarda los ítems, sube la versión y deja la solicitud en Cotizada.
@transaction.atomic
def emitir_cotizacion(solicitud, cotizacion, items, usuario, request=None):
    nueva = cotizacion.pk is None
    if not nueva:
        cotizacion.version += 1
    cotizacion.solicitud = solicitud
    cotizacion.items = items
    cotizacion.monto = sum(item['subtotal'] for item in items)
    cotizacion.emitida_por = usuario
    cotizacion.fecha_emision = timezone.now()
    cotizacion.respuesta_cliente = ''
    cotizacion.comentario_cliente = ''
    cotizacion.fecha_respuesta = None
    cotizacion.save()
    solicitud.cotizacion = cotizacion
    cotizada = EstadoSolicitud.obtener(EstadoSolicitud.COTIZADA)
    texto = 'Cotización formal emitida.' if nueva else f'Cotización actualizada a la versión {cotizacion.version}.'
    if solicitud.estado_id != cotizada.pk:
        cambiar_estado(solicitud, cotizada, usuario, texto, notificar=False, request=request)
    else:
        registrar_historial(solicitud, cotizada, texto, usuario)
    auditoria.registrar(request, 'cotizacion', f'{solicitud.numero}: cotización versión {cotizacion.version}', solicitud, usuario)
    transaction.on_commit(lambda: notificaciones.cotizacion_emitida(solicitud, request))
    return cotizacion


# CU12 Responder cotización: el cliente acepta (Aprobada) o rechaza (Cotización rechazada).
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
    cambiar_estado(solicitud, EstadoSolicitud.obtener(codigo), usuario, texto, notificar=False, request=request)
    transaction.on_commit(lambda: notificaciones.cotizacion_respondida(solicitud, request))


# Cancela la solicitud y avisa al equipo.
@transaction.atomic
def cancelar_solicitud(solicitud, usuario, request=None):
    cambiar_estado(solicitud, EstadoSolicitud.obtener(EstadoSolicitud.CANCELADA), usuario, 'Solicitud cancelada por el cliente.', notificar=False, request=request)
    transaction.on_commit(lambda: notificaciones.solicitud_cancelada(solicitud, request))


# Asigna un integrante del equipo a la solicitud y le avisa por correo.
@transaction.atomic
def asignar_responsable(solicitud, responsable, usuario, request=None):
    if solicitud.responsable_id == (responsable.pk if responsable else None):
        return False
    solicitud.responsable = responsable
    solicitud.save(update_fields=['responsable', 'fecha_actualizacion'])
    nombre = (responsable.get_full_name() or responsable.email) if responsable else 'sin responsable'
    auditoria.registrar(request, 'asignacion', f'{solicitud.numero}: asignada a {nombre}', solicitud, usuario)
    if responsable is not None and responsable != usuario:
        transaction.on_commit(lambda: notificaciones.responsable_asignado(solicitud, request))
    return True


# CU13 Conversar con el equipo: guarda el mensaje y notifica a la otra parte.
@transaction.atomic
def enviar_mensaje(solicitud, autor, texto, request=None):
    mensaje = MensajeSolicitud.objects.create(
        solicitud=solicitud,
        autor=autor,
        es_equipo=autor.is_staff and autor.pk != solicitud.cliente_id,
        texto=texto,
    )
    Solicitud.objects.filter(pk=solicitud.pk).update(fecha_actualizacion=timezone.now())
    if mensaje.es_equipo:
        auditoria.registrar(request, 'mensaje', f'{solicitud.numero}: mensaje enviado al cliente', solicitud, autor)
    transaction.on_commit(lambda: notificaciones.mensaje_nuevo(mensaje, request))
    return mensaje


# Marca como leídos los mensajes que vio el usuario.
def marcar_mensajes_leidos(solicitud, lector):
    del_equipo = not (lector.is_staff and lector.pk != solicitud.cliente_id)
    return MensajeSolicitud.objects.filter(solicitud=solicitud, es_equipo=del_equipo, leido=False).update(leido=True)


# CU10 Adjuntar archivos: guarda el archivo y su registro en plataforma_adjunto.
def guardar_adjunto(solicitud, archivo, usuario, es_equipo=False, request=None):
    adjunto = Adjunto.objects.create(
        solicitud=solicitud,
        archivo=archivo,
        nombre_original=archivo.name[:255],
        tamano=archivo.size,
        tipo_contenido=(getattr(archivo, 'content_type', '') or '')[:120],
        subido_por=usuario,
        es_equipo=es_equipo,
    )
    if es_equipo:
        auditoria.registrar(request, 'adjunto', f'{solicitud.numero}: archivo {adjunto.nombre_original}', solicitud, usuario)
    return adjunto
