from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.datastructures import MultiValueDict
from django.views.decorators.http import require_POST

from .. import gestion
from ..estimacion import (
    FUNCIONALIDADES,
    INTEGRACIONES,
    calcular_estimacion,
    nombres_funcionalidades,
    nombres_integraciones,
    nombres_objetivos,
)
from ..forms import (
    RespuestaCotizacionForm,
    SolicitudMantenimientoForm,
    SolicitudMejoraForm,
    SolicitudSoporteForm,
    SolicitudWebForm,
)
from ..models import EstadoSolicitud, RequerimientoWeb, Servicio, Solicitud

CLAVE_BORRADOR = 'axztra_borrador_web'

INFO_TIPOS_SITIO = {
    'landing': {'icono': 'fa-solid fa-bullseye', 'descripcion': 'Una sola página para presentar una oferta o captar contactos.'},
    'corporativo': {'icono': 'fa-regular fa-building', 'descripcion': 'Varias secciones para presentar tu empresa y servicios.'},
    'portafolio': {'icono': 'fa-regular fa-images', 'descripcion': 'Muestra trabajos, proyectos o publicaciones.'},
    'servicios': {'icono': 'fa-regular fa-calendar-check', 'descripcion': 'Para negocios que reciben reservas u horas.'},
    'tienda': {'icono': 'fa-solid fa-store', 'descripcion': 'Vende productos en línea con carrito de compras.'},
}

INFO_COMPLEJIDAD = {
    'basica': {'icono': 'fa-solid fa-circle', 'descripcion': 'Diseño limpio a partir de una plantilla adaptada a tu marca.'},
    'media': {'icono': 'fa-solid fa-circle-half-stroke', 'descripcion': 'Diseño personalizado con secciones a medida.'},
    'alta': {'icono': 'fa-solid fa-star', 'descripcion': 'Diseño exclusivo, animaciones y detalles avanzados.'},
}

INFO_SITIO_ACTUAL = {
    'no': {'icono': 'fa-solid fa-seedling', 'descripcion': 'Partimos desde cero.'},
    'si': {'icono': 'fa-solid fa-globe', 'descripcion': 'Lo tomaremos como referencia.'},
}


def _servicio_inicial(request, tipo):
    servicio_id = request.GET.get('servicio', '')
    if servicio_id.isdigit() and Servicio.objects.filter(pk=servicio_id, tipo=tipo, activo=True).exists():
        return {'servicio': int(servicio_id)}
    return {}


def _servicio_actual(form):
    if form.is_bound and form.is_valid():
        return form.cleaned_data.get('servicio')
    valor = form.initial.get('servicio')
    return Servicio.objects.filter(pk=valor).first() if valor else None


@login_required
def nueva_solicitud(request):
    return render(request, 'plataforma/solicitudes/nueva.html')


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
        form = SolicitudWebForm(initial=_servicio_inicial(request, Servicio.TIPO_CREACION))

    return render(request, 'plataforma/solicitudes/crear_web.html', {
        'form': form,
        'paso_inicial': form.primer_paso_con_error if form.is_bound else 1,
        'funcionalidades': FUNCIONALIDADES,
        'integraciones': INTEGRACIONES,
        'info_tipos': INFO_TIPOS_SITIO,
        'info_complejidad': INFO_COMPLEJIDAD,
        'info_sitio_actual': INFO_SITIO_ACTUAL,
        'servicio': _servicio_actual(form),
        'asistente_invitacion': '¿Necesitas ayuda para completar este formulario? Pregúntame lo que quieras.',
        'asistente_saludo': 'Estoy aquí para ayudarte con el formulario. Puedo explicarte qué tipo de sitio elegir, qué significa cada funcionalidad o cómo se calcula la estimación.',
    })


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
        solicitud = gestion.crear_solicitud_web(request.user, datos, request)
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
    })


def _solicitud_simple(request, form_clase, tipo, plantilla, armar_detalles, prioridad=lambda datos: 'media'):
    if request.method == 'POST':
        form = form_clase(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            solicitud = gestion.crear_solicitud(
                request.user,
                tipo,
                datos,
                detalles=armar_detalles(form, datos),
                prioridad=prioridad(datos),
                request=request,
            )
            messages.success(request, f'Recibimos tu solicitud {solicitud.numero}. Puedes seguir su avance desde aquí.')
            return redirect(solicitud.get_absolute_url())
    else:
        form = form_clase(initial=_servicio_inicial(request, tipo))
    return render(request, plantilla, {'form': form, 'servicio': _servicio_actual(form)})


def _etiquetas(opciones, claves):
    mapa = dict(opciones)
    return [mapa[c] for c in claves if c in mapa]


@login_required
def solicitar_mejora(request):
    return _solicitud_simple(
        request,
        SolicitudMejoraForm,
        Servicio.TIPO_MEJORA,
        'plataforma/solicitudes/mejora.html',
        lambda form, datos: {'Mejoras solicitadas': _etiquetas(form.TIPOS_MEJORA, datos['tipos_mejora'])},
    )


@login_required
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


@login_required
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


@login_required
def mis_solicitudes(request):
    solicitudes = request.user.solicitudes.select_related('estado', 'servicio')
    filtro = request.GET.get('filtro', 'todas')
    if filtro == 'activas':
        solicitudes = solicitudes.filter(estado__es_final=False)
    elif filtro == 'cerradas':
        solicitudes = solicitudes.filter(estado__es_final=True)
    else:
        filtro = 'todas'
    pagina = Paginator(solicitudes, 10).get_page(request.GET.get('pagina'))
    base = request.user.solicitudes
    return render(request, 'plataforma/cliente/mis_solicitudes.html', {
        'pagina': pagina,
        'filtro': filtro,
        'conteo': {
            'todas': base.count(),
            'activas': base.filter(estado__es_final=False).count(),
            'cerradas': base.filter(estado__es_final=True).count(),
            'por_responder': base.filter(estado__codigo=EstadoSolicitud.COTIZADA).count(),
        },
    })


def _solicitud_del_cliente(request, pk):
    consulta = Solicitud.objects.select_related('estado', 'servicio', 'requerimiento', 'cliente')
    if request.user.is_staff:
        return get_object_or_404(consulta, pk=pk)
    return get_object_or_404(consulta, pk=pk, cliente=request.user)


@login_required
def ver_solicitud(request, pk):
    solicitud = _solicitud_del_cliente(request, pk)
    requerimiento = solicitud.requerimiento
    contexto = {
        'solicitud': solicitud,
        'historial': solicitud.historial.select_related('estado_nuevo', 'estado_anterior'),
        'estimacion': getattr(solicitud, 'estimacion', None),
        'cotizacion': getattr(solicitud, 'cotizacion', None),
        'form_respuesta': RespuestaCotizacionForm(),
        'es_duenio': solicitud.cliente_id == request.user.pk,
    }
    if requerimiento:
        contexto.update({
            'objetivos': nombres_objetivos(requerimiento.objetivos),
            'funcionalidades': nombres_funcionalidades(requerimiento.funcionalidades),
            'integraciones': nombres_integraciones(requerimiento.integraciones),
        })
    return render(request, 'plataforma/cliente/ver_solicitud.html', contexto)


@login_required
@require_POST
def responder_cotizacion(request, pk):
    solicitud = get_object_or_404(Solicitud.objects.select_related('estado'), pk=pk, cliente=request.user)
    if not solicitud.cotizacion_pendiente:
        messages.error(request, 'Esta solicitud no tiene una cotización pendiente de respuesta.')
        return redirect(solicitud.get_absolute_url())
    if not solicitud.cotizacion.vigente:
        messages.error(request, 'La cotización venció. Escríbenos para emitir una actualizada.')
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
