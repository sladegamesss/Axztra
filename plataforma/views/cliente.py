"""
Vistas del cliente: crear solicitudes y seguirlas.

Casos de uso: CU08 Solicitar servicio, CU09 Levantar requerimientos, CU02 Obtener estimación,
CU10 Adjuntar archivos, CU11 Consultar mis solicitudes, CU12 Responder cotización y CU13 Conversar con el equipo.
El formulario de creación de sitios sigue el diagrama de actividades DA-02 del informe.
"""

import mimetypes

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.datastructures import MultiValueDict
from django.views.decorators.http import require_POST

from .. import gestion
from ..estimacion import (
    FUNCIONALIDADES,
    INTEGRACIONES,
    calcular_estimacion,
    configuracion_publica,
    nombres_funcionalidades,
    nombres_integraciones,
    nombres_objetivos,
)
from ..forms import (
    AdjuntoForm,
    MensajeForm,
    RespuestaCotizacionForm,
    SolicitudMantenimientoForm,
    SolicitudMejoraForm,
    SolicitudSoporteForm,
    SolicitudWebForm,
)
from ..models import Adjunto, EstadoSolicitud, RequerimientoWeb, Servicio, Solicitud
from ..seguridad import limitar

# Las respuestas del formulario se guardan en la sesión hasta que el cliente confirma el envío.
CLAVE_BORRADOR = 'axztra_borrador_web'

# Íconos y descripciones que se muestran en las opciones del formulario.
INFO_TIPOS_SITIO = {
    'landing': {'icono': 'fa-solid fa-bullseye', 'descripcion': 'Una sola página para presentar una oferta o captar contactos.'},
    'corporativo': {'icono': 'fa-regular fa-building', 'descripcion': 'Varias secciones para presentar tu empresa y servicios.'},
    'portafolio': {'icono': 'fa-regular fa-images', 'descripcion': 'Muestra trabajos, proyectos o publicaciones.'},
    'servicios': {'icono': 'fa-regular fa-calendar-check', 'descripcion': 'Para negocios que reciben reservas u horas.'},
    'tienda': {'icono': 'fa-solid fa-store', 'descripcion': 'Vende productos en línea con carro de compras.'},
}

INFO_COMPLEJIDAD = {
    'basica': {'icono': 'fa-regular fa-square', 'descripcion': 'Diseño limpio a partir de una base adaptada a tu marca.'},
    'media': {'icono': 'fa-solid fa-table-cells-large', 'descripcion': 'Diseño personalizado con secciones a medida.'},
    'alta': {'icono': 'fa-solid fa-wand-magic-sparkles', 'descripcion': 'Diseño exclusivo con animaciones y detalles avanzados.'},
}

INFO_SITIO_ACTUAL = {
    'no': {'icono': 'fa-solid fa-seedling', 'descripcion': 'Partimos desde cero.'},
    'si': {'icono': 'fa-solid fa-globe', 'descripcion': 'Lo usaremos como referencia.'},
}

INFO_ESTILOS = {
    'sin_preferencia': {'icono': 'fa-regular fa-circle-question', 'descripcion': 'Lo definimos juntos según tu rubro.'},
    'moderno': {'icono': 'fa-solid fa-bolt', 'descripcion': 'Líneas limpias y elementos actuales.'},
    'minimalista': {'icono': 'fa-regular fa-square', 'descripcion': 'Pocos elementos y mucho espacio.'},
    'elegante': {'icono': 'fa-regular fa-gem', 'descripcion': 'Tipografías finas y tonos sobrios.'},
    'colorido': {'icono': 'fa-solid fa-palette', 'descripcion': 'Colores vivos que llaman la atención.'},
    'corporativo': {'icono': 'fa-regular fa-building', 'descripcion': 'Serio y ordenado, ideal para empresas.'},
}

INFO_LOGO = {
    'tiene': {'icono': 'fa-regular fa-circle-check', 'descripcion': 'Lo usaremos en el diseño.'},
    'mejorar': {'icono': 'fa-solid fa-pen-ruler', 'descripcion': 'Lo actualizamos junto con el sitio.'},
    'crear': {'icono': 'fa-solid fa-wand-magic-sparkles', 'descripcion': 'Se cotiza aparte del sitio.'},
}

# Textos del asistente virtual. Solo aparece en las pantallas para crear una solicitud.
SALUDO_ASISTENTE = 'Estoy aquí para ayudarte con tu solicitud. Puedo explicarte qué tipo de sitio elegir, qué significa cada funcionalidad o cómo se calcula la estimación.'
INVITACION_ASISTENTE = '¿Te ayudo a completar el formulario? Puedo sugerir funcionalidades según tu negocio.'


# Si el cliente llegó desde la ficha de un servicio, lo deja preseleccionado.
def _servicio_inicial(request, tipo):
    servicio_id = request.GET.get('servicio', '')
    if servicio_id.isdigit() and Servicio.objects.filter(pk=servicio_id, tipo=tipo, activo=True).exists():
        return {'servicio': int(servicio_id)}
    return {}


# Servicio elegido en el formulario, para mostrarlo en el encabezado.
def _servicio_actual(form):
    if form.is_bound:
        if form.is_valid():
            return form.cleaned_data.get('servicio')
        valor = form.data.get('servicio')
    else:
        valor = form.initial.get('servicio')
    if valor and str(valor).isdigit():
        return Servicio.objects.filter(pk=valor).first()
    return None


# CU08: pantalla para elegir el tipo de solicitud (crear, mejorar, soporte o mantenimiento).
@login_required
def nueva_solicitud(request):
    return render(request, 'plataforma/solicitudes/nueva.html')


# CU08 + CU09: formulario de cuatro pasos para crear una página web (DA-02).
# Si los datos son válidos se guardan en la sesión y se pasa a la estimación.
@login_required
def crear_web(request):
    if request.method == 'POST':
        form = SolicitudWebForm(request.POST)
        if form.is_valid():
            request.session[CLAVE_BORRADOR] = {
                clave: valores for clave, valores in request.POST.lists() if clave != 'csrfmiddlewaretoken'
            }
            return redirect('estimacion_web')
    elif request.GET.get('editar') and request.session.get(CLAVE_BORRADOR):
        form = SolicitudWebForm(MultiValueDict(request.session[CLAVE_BORRADOR]))
    else:
        inicial = {**SolicitudWebForm.inicial_desde_parametros(request.GET), **_servicio_inicial(request, Servicio.TIPO_CREACION)}
        form = SolicitudWebForm(initial=inicial)

    return render(request, 'plataforma/solicitudes/crear_web.html', {
        'form': form,
        'paso_inicial': form.primer_paso_con_error if form.is_bound else 1,
        'funcionalidades': FUNCIONALIDADES,
        'integraciones': INTEGRACIONES,
        'info_tipos': INFO_TIPOS_SITIO,
        'info_complejidad': INFO_COMPLEJIDAD,
        'info_sitio_actual': INFO_SITIO_ACTUAL,
        'info_estilos': INFO_ESTILOS,
        'info_logo': INFO_LOGO,
        'config_estimacion': configuracion_publica(),
        'servicio': _servicio_actual(form),
        'asistente_invitacion': INVITACION_ASISTENTE,
        'asistente_saludo': SALUDO_ASISTENTE,
    })


# CU02 Obtener estimación: muestra el rango referencial y el resumen.
# Al confirmar (POST) se registra la solicitud en estado Recibida.
@login_required
def estimacion_web(request):
    borrador = request.session.get(CLAVE_BORRADOR)
    if not borrador:
        messages.info(request, 'Completa el formulario para obtener tu estimación.')
        return redirect('crear_web')

    form = SolicitudWebForm(MultiValueDict(borrador))
    if not form.is_valid():
        messages.warning(request, 'Revisa los datos del formulario antes de continuar.')
        return redirect(f"{reverse('crear_web')}?editar=1")

    datos = form.cleaned_data
    if request.method == 'POST':
        try:
            solicitud = gestion.crear_solicitud_web(request.user, datos, request, token=datos.get('token_envio'))
        except gestion.SolicitudDuplicada as duplicada:
            request.session.pop(CLAVE_BORRADOR, None)
            messages.info(request, f'Esta solicitud ya estaba registrada con el número {duplicada.solicitud.numero}.')
            return redirect(duplicada.solicitud.get_absolute_url())
        request.session.pop(CLAVE_BORRADOR, None)
        messages.success(request, f'Recibimos tu solicitud {solicitud.numero}. Te avisaremos por correo cuando la cotización esté lista.')
        return redirect(solicitud.get_absolute_url())

    resultado = calcular_estimacion(
        datos['tipo_sitio'], datos['complejidad'], datos['num_paginas'], datos['funcionalidades'], datos['integraciones']
    )
    return render(request, 'plataforma/solicitudes/estimacion.html', {
        'datos': datos,
        'estimacion': resultado,
        'tipo_sitio': dict(RequerimientoWeb.TIPOS_SITIO).get(datos['tipo_sitio']),
        'complejidad': dict(RequerimientoWeb.COMPLEJIDADES).get(datos['complejidad']),
        'objetivos': nombres_objetivos(datos['objetivos']),
        'funcionalidades': nombres_funcionalidades(datos['funcionalidades']),
        'integraciones': nombres_integraciones(datos['integraciones']),
        'estilo': dict(RequerimientoWeb.ESTILOS).get(datos['estilo_visual']),
        'secciones': _etiquetas(RequerimientoWeb.SECCIONES, datos['secciones']),
        'logo': dict(RequerimientoWeb.OPCIONES_LOGO).get(datos['situacion_logo']),
        'presupuesto': dict(RequerimientoWeb.PRESUPUESTOS).get(datos['presupuesto']),
        'medio_contacto': dict(RequerimientoWeb.MEDIOS_CONTACTO).get(datos['medio_contacto']),
        'asistente_saludo': SALUDO_ASISTENTE,
    })


# Lógica común de los formularios de mejora, soporte y mantenimiento.
def _solicitud_simple(request, form_clase, tipo, plantilla, armar_detalles, prioridad=lambda datos: 'media'):
    if request.method == 'POST':
        form = form_clase(request.POST, request.FILES, cliente=request.user)
        if form.is_valid():
            datos = form.cleaned_data
            try:
                solicitud = gestion.crear_solicitud(
                    request.user,
                    tipo,
                    datos,
                    detalles=armar_detalles(form, datos),
                    prioridad=prioridad(datos),
                    request=request,
                    token=datos.get('token_envio'),
                )
            except gestion.SolicitudDuplicada as duplicada:
                messages.info(request, f'Esta solicitud ya estaba registrada con el número {duplicada.solicitud.numero}.')
                return redirect(duplicada.solicitud.get_absolute_url())
            messages.success(request, f'Recibimos tu solicitud {solicitud.numero}. Puedes seguir su avance desde aquí.')
            return redirect(solicitud.get_absolute_url())
    else:
        form = form_clase(initial=_servicio_inicial(request, tipo), cliente=request.user)
    return render(request, plantilla, {'form': form, 'servicio': _servicio_actual(form)})


# Convierte códigos de opciones en sus nombres.
def _etiquetas(opciones, claves):
    mapa = dict(opciones)
    return [mapa[c] for c in claves if c in mapa]


# CU08: solicitud de mejora de un sitio existente.
@login_required
@limitar('solicitud', 20, 3600, por_usuario=True)
def solicitar_mejora(request):
    return _solicitud_simple(
        request,
        SolicitudMejoraForm,
        Servicio.TIPO_MEJORA,
        'plataforma/solicitudes/mejora.html',
        lambda form, datos: {'Mejoras solicitadas': _etiquetas(form.TIPOS_MEJORA, datos['tipos_mejora'])},
    )


# CU08: solicitud de soporte técnico (la prioridad depende de la urgencia).
@login_required
@limitar('solicitud', 20, 3600, por_usuario=True)
def solicitar_soporte(request):
    return _solicitud_simple(
        request,
        SolicitudSoporteForm,
        Servicio.TIPO_SOPORTE,
        'plataforma/solicitudes/soporte.html',
        lambda form, datos: {
            'Tipo de problema': dict(form.TIPOS_PROBLEMA)[datos['tipo_problema']],
            'Ocurre desde': datos.get('desde_cuando') or 'No indicado',
        },
        prioridad=lambda datos: datos['prioridad'],
    )


# CU08: solicitud de mantenimiento periódico.
@login_required
@limitar('solicitud', 20, 3600, por_usuario=True)
def solicitar_mantenimiento(request):
    return _solicitud_simple(
        request,
        SolicitudMantenimientoForm,
        Servicio.TIPO_MANTENIMIENTO,
        'plataforma/solicitudes/mantenimiento.html',
        lambda form, datos: {
            'Plataforma': dict(form.PLATAFORMAS)[datos['plataforma']],
            'Frecuencia': dict(form.FRECUENCIAS)[datos['frecuencia']],
            'Tareas': _etiquetas(form.TAREAS, datos['tareas']),
        },
    )


# CU11 Consultar mis solicitudes: listado con filtros por estado.
@login_required
def mis_solicitudes(request):
    base = request.user.solicitudes.all()
    solicitudes = base.select_related('estado', 'servicio', 'responsable').annotate(
        no_leidos=Count('mensajes', filter=Q(mensajes__es_equipo=True, mensajes__leido=False))
    ).order_by('-fecha_solicitud', '-pk')
    filtro = request.GET.get('filtro', 'todas')
    if filtro == 'activas':
        solicitudes = solicitudes.filter(estado__es_final=False)
    elif filtro == 'cerradas':
        solicitudes = solicitudes.filter(estado__es_final=True)
    elif filtro == 'responder':
        solicitudes = solicitudes.filter(estado__codigo=EstadoSolicitud.COTIZADA)
    else:
        filtro = 'todas'
    busqueda = request.GET.get('q', '').strip()[:80]
    if busqueda:
        solicitudes = solicitudes.filter(Q(numero__icontains=busqueda) | Q(titulo__icontains=busqueda))
    pagina = Paginator(solicitudes, 10).get_page(request.GET.get('pagina'))
    conteo = base.aggregate(
        todas=Count('pk'),
        activas=Count('pk', filter=Q(estado__es_final=False)),
        cerradas=Count('pk', filter=Q(estado__es_final=True)),
        responder=Count('pk', filter=Q(estado__codigo=EstadoSolicitud.COTIZADA)),
    )
    return render(request, 'plataforma/cliente/mis_solicitudes.html', {
        'pagina': pagina,
        'filtro': filtro,
        'busqueda': busqueda,
        'conteo': conteo,
    })


# Obtiene la solicitud solo si pertenece al cliente que la pide.
def _solicitud_visible(request, pk):
    consulta = Solicitud.objects.select_related('estado', 'servicio', 'requerimiento', 'cliente', 'responsable', 'relacionada')
    if request.user.is_staff:
        return get_object_or_404(consulta, pk=pk)
    return get_object_or_404(consulta, pk=pk, cliente=request.user)


# CU11: detalle con etapas, historial, estimación, cotización, mensajes y archivos.
@login_required
def ver_solicitud(request, pk):
    solicitud = _solicitud_visible(request, pk)
    es_duenio = solicitud.cliente_id == request.user.pk
    if es_duenio:
        gestion.marcar_mensajes_leidos(solicitud, request.user)
    requerimiento = solicitud.requerimiento
    contexto = {
        'solicitud': solicitud,
        'historial': solicitud.historial.select_related('estado_nuevo', 'estado_anterior'),
        'mensajes_solicitud': solicitud.mensajes.select_related('autor'),
        'adjuntos': solicitud.adjuntos.select_related('subido_por'),
        'derivadas': solicitud.derivadas.select_related('estado') if es_duenio else [],
        'estimacion': getattr(solicitud, 'estimacion', None),
        'cotizacion': getattr(solicitud, 'cotizacion', None),
        'form_respuesta': RespuestaCotizacionForm(),
        'form_mensaje': MensajeForm(),
        'form_adjunto': AdjuntoForm(),
        'es_duenio': es_duenio,
        'puede_escribir': es_duenio and solicitud.cliente.is_active,
    }
    if requerimiento:
        contexto.update({
            'objetivos': nombres_objetivos(requerimiento.objetivos),
            'funcionalidades': nombres_funcionalidades(requerimiento.funcionalidades),
            'integraciones': nombres_integraciones(requerimiento.integraciones),
        })
    return render(request, 'plataforma/cliente/ver_solicitud.html', contexto)


# CU13 Conversar con el equipo.
@login_required
@require_POST
@limitar('mensaje', 30, 600, por_usuario=True)
def enviar_mensaje(request, pk):
    solicitud = get_object_or_404(Solicitud.objects.select_related('cliente', 'responsable'), pk=pk, cliente=request.user)
    form = MensajeForm(request.POST)
    if form.is_valid():
        gestion.enviar_mensaje(solicitud, request.user, form.cleaned_data['texto'], request)
        messages.success(request, 'Mensaje enviado. Te avisaremos por correo cuando el equipo responda.')
    else:
        messages.error(request, form.errors.get('texto', ['No pudimos enviar el mensaje.'])[0])
    return redirect(f'{solicitud.get_absolute_url()}#mensajes')


# CU10 Adjuntar archivos a la solicitud.
@login_required
@require_POST
@limitar('adjunto', 20, 3600, por_usuario=True)
def subir_adjunto(request, pk):
    solicitud = get_object_or_404(Solicitud, pk=pk, cliente=request.user)
    form = AdjuntoForm(request.POST, request.FILES)
    if form.is_valid():
        gestion.guardar_adjunto(solicitud, form.cleaned_data['archivo'], request.user, es_equipo=False, request=request)
        messages.success(request, 'Archivo adjuntado a la solicitud.')
    else:
        messages.error(request, form.errors.get('archivo', ['No pudimos adjuntar el archivo.'])[0])
    return redirect(f'{solicitud.get_absolute_url()}#archivos')


# Entrega un archivo solo al dueño de la solicitud o al equipo (los archivos son privados).
@login_required
def descargar_adjunto(request, pk):
    adjunto = get_object_or_404(Adjunto.objects.select_related('solicitud'), pk=pk)
    if not request.user.is_staff and adjunto.solicitud.cliente_id != request.user.pk:
        raise Http404
    try:
        archivo = adjunto.archivo.open('rb')
    except (FileNotFoundError, OSError):
        raise Http404
    tipo = adjunto.tipo_contenido or mimetypes.guess_type(adjunto.nombre_original)[0] or 'application/octet-stream'
    respuesta = FileResponse(archivo, as_attachment=True, filename=adjunto.nombre_original, content_type=tipo)
    respuesta['X-Content-Type-Options'] = 'nosniff'
    return respuesta


# Versión imprimible de la cotización (se puede guardar como PDF).
@login_required
def cotizacion_documento(request, pk):
    solicitud = _solicitud_visible(request, pk)
    cotizacion = getattr(solicitud, 'cotizacion', None)
    if cotizacion is None:
        raise Http404
    perfil = getattr(solicitud.cliente, 'perfil_cliente', None)
    return render(request, 'plataforma/cliente/cotizacion_documento.html', {
        'solicitud': solicitud,
        'cotizacion': cotizacion,
        'perfil': perfil,
    })


# CU12 Responder cotización: aceptar o rechazar.
@login_required
@require_POST
def responder_cotizacion(request, pk):
    solicitud = get_object_or_404(Solicitud.objects.select_related('estado'), pk=pk, cliente=request.user)
    if not solicitud.cotizacion_pendiente:
        messages.error(request, 'Esta solicitud no tiene una cotización pendiente de respuesta.')
        return redirect(solicitud.get_absolute_url())
    if not solicitud.cotizacion.vigente:
        messages.error(request, 'La cotización venció. Escríbenos desde los mensajes de la solicitud para emitir una actualizada.')
        return redirect(solicitud.get_absolute_url())
    form = RespuestaCotizacionForm(request.POST)
    if form.is_valid():
        respuesta = form.cleaned_data['respuesta']
        gestion.responder_cotizacion(solicitud, respuesta, form.cleaned_data['comentario'], request.user, request)
        if respuesta == 'aceptada':
            messages.success(request, 'Aceptaste la cotización. El equipo se pondrá en contacto para coordinar el inicio.')
        else:
            messages.info(request, 'Registramos que rechazaste la cotización. Gracias por avisarnos.')
    else:
        messages.error(request, 'No pudimos registrar tu respuesta. Intenta nuevamente.')
    return redirect(solicitud.get_absolute_url())


# Permite al cliente cancelar mientras no tenga cotización.
@login_required
@require_POST
def cancelar_solicitud(request, pk):
    solicitud = get_object_or_404(Solicitud.objects.select_related('estado'), pk=pk, cliente=request.user)
    if not solicitud.cancelable:
        messages.error(request, 'Esta solicitud ya no se puede cancelar desde la plataforma.')
    else:
        gestion.cancelar_solicitud(solicitud, request.user, request)
        messages.success(request, f'La solicitud {solicitud.numero} fue cancelada.')
    return redirect(solicitud.get_absolute_url())
