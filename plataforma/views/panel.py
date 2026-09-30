from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .. import gestion
from ..decoradores import staff_verificado
from ..estimacion import nombres_funcionalidades, nombres_integraciones, nombres_objetivos
from ..forms import CambioEstadoForm, CategoriaForm, CotizacionForm, GestionInternaForm, ServicioForm
from ..models import Categoria, Cotizacion, EstadoSolicitud, Estimacion, MensajeAsistente, Servicio, Solicitud

User = get_user_model()

ETIQUETAS_INTENCION = {
    'saludo': 'Saludos',
    'agradecimiento': 'Agradecimientos',
    'creacion': 'Crear un sitio',
    'tienda': 'Tiendas online',
    'estimacion': 'Precios',
    'plazos': 'Plazos',
    'mejora': 'Mejoras',
    'soporte': 'Soporte técnico',
    'mantenimiento': 'Mantenimiento',
    'seguimiento': 'Seguimiento',
    'pagos': 'Pagos',
    'cuenta': 'Cuenta de usuario',
    'contacto': 'Contacto',
    'servicios': 'Servicios',
    'hosting': 'Dominio y hosting',
    'no_entendido': 'No reconocidas',
    'vacio': 'Mensajes vacíos',
}


@staff_verificado
def panel_inicio(request):
    ahora = timezone.now()
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    hace_30 = ahora - timedelta(days=30)
    solicitudes = Solicitud.objects.all()
    total = solicitudes.count()

    por_estado = list(
        EstadoSolicitud.objects.annotate(cantidad=Count('solicitudes')).order_by('orden')
    )
    por_tipo = []
    conteo_tipos = dict(solicitudes.order_by().values_list('tipo').annotate(c=Count('pk')))
    for clave, nombre in Solicitud.TIPOS:
        por_tipo.append({'nombre': nombre, 'cantidad': conteo_tipos.get(clave, 0)})

    monto_aprobado = Cotizacion.objects.filter(respuesta_cliente='aceptada').aggregate(s=Sum('monto'))['s'] or 0
    monto_en_estimacion = Estimacion.objects.filter(solicitud__estado__es_final=False).aggregate(s=Sum('total'))['s'] or 0

    return render(request, 'plataforma/panel/inicio.html', {
        'seccion': 'inicio',
        'total': total,
        'nuevas_mes': solicitudes.filter(fecha_solicitud__gte=inicio_mes).count(),
        'por_atender': solicitudes.filter(estado__codigo=EstadoSolicitud.RECIBIDA).count(),
        'clientes': User.objects.filter(is_staff=False).count(),
        'clientes_mes': User.objects.filter(is_staff=False, date_joined__gte=inicio_mes).count(),
        'monto_aprobado': monto_aprobado,
        'monto_en_estimacion': monto_en_estimacion,
        'consultas': MensajeAsistente.objects.filter(es_asistente=False, fecha__gte=hace_30).count(),
        'por_estado': por_estado,
        'max_estado': max([e.cantidad for e in por_estado] + [1]),
        'por_tipo': por_tipo,
        'max_tipo': max([t['cantidad'] for t in por_tipo] + [1]),
        'recientes': solicitudes.select_related('estado', 'cliente')[:8],
        'urgentes': solicitudes.filter(prioridad__in=['alta', 'urgente'], estado__es_final=False).select_related('estado', 'cliente')[:5],
    })


@staff_verificado
def panel_solicitudes(request):
    solicitudes = Solicitud.objects.select_related('estado', 'cliente', 'estimacion')
    estado = request.GET.get('estado', '')
    tipo = request.GET.get('tipo', '')
    prioridad = request.GET.get('prioridad', '')
    busqueda = request.GET.get('q', '').strip()

    if estado:
        solicitudes = solicitudes.filter(estado__codigo=estado)
    if tipo in dict(Solicitud.TIPOS):
        solicitudes = solicitudes.filter(tipo=tipo)
    if prioridad in dict(Solicitud.PRIORIDADES):
        solicitudes = solicitudes.filter(prioridad=prioridad)
    if busqueda:
        solicitudes = solicitudes.filter(
            Q(numero__icontains=busqueda)
            | Q(titulo__icontains=busqueda)
            | Q(cliente__email__icontains=busqueda)
            | Q(cliente__first_name__icontains=busqueda)
            | Q(cliente__last_name__icontains=busqueda)
        )

    pagina = Paginator(solicitudes, 15).get_page(request.GET.get('pagina'))
    return render(request, 'plataforma/panel/solicitudes.html', {
        'seccion': 'solicitudes',
        'pagina': pagina,
        'estados': EstadoSolicitud.objects.all(),
        'tipos': Solicitud.TIPOS,
        'prioridades': Solicitud.PRIORIDADES,
        'filtros': {'estado': estado, 'tipo': tipo, 'prioridad': prioridad, 'q': busqueda},
    })


@staff_verificado
def panel_solicitud(request, pk):
    solicitud = get_object_or_404(
        Solicitud.objects.select_related('estado', 'cliente', 'servicio', 'requerimiento'), pk=pk
    )
    cotizacion = getattr(solicitud, 'cotizacion', None)
    form_estado = CambioEstadoForm(solicitud=solicitud)
    form_cotizacion = CotizacionForm(instance=cotizacion, initial=_cotizacion_sugerida(solicitud) if cotizacion is None else None)
    form_gestion = GestionInternaForm(instance=solicitud)
    accion = request.POST.get('accion') if request.method == 'POST' else None

    if accion == 'estado':
        form_estado = CambioEstadoForm(request.POST, solicitud=solicitud)
        if form_estado.is_valid():
            datos = form_estado.cleaned_data
            gestion.cambiar_estado(solicitud, datos['estado'], request.user, datos['comentario'], datos['notificar'], request)
            messages.success(request, f"Estado actualizado a «{datos['estado'].nombre}».")
            return redirect('panel_solicitud', pk=solicitud.pk)
    elif accion == 'cotizacion':
        if solicitud.estado.es_final and solicitud.estado.codigo != EstadoSolicitud.RECHAZADA:
            messages.error(request, 'No se puede cotizar una solicitud cerrada.')
            return redirect('panel_solicitud', pk=solicitud.pk)
        form_cotizacion = CotizacionForm(request.POST, instance=cotizacion)
        if form_cotizacion.is_valid():
            gestion.emitir_cotizacion(solicitud, form_cotizacion, request.user, request)
            messages.success(request, 'Cotización emitida y enviada al cliente.')
            return redirect('panel_solicitud', pk=solicitud.pk)
    elif accion == 'gestion':
        form_gestion = GestionInternaForm(request.POST, instance=solicitud)
        if form_gestion.is_valid():
            form_gestion.save()
            messages.success(request, 'Datos internos guardados.')
            return redirect('panel_solicitud', pk=solicitud.pk)

    requerimiento = solicitud.requerimiento
    contexto = {
        'seccion': 'solicitudes',
        'solicitud': solicitud,
        'cotizacion': cotizacion,
        'estimacion': getattr(solicitud, 'estimacion', None),
        'historial': solicitud.historial.select_related('estado_nuevo', 'estado_anterior', 'usuario'),
        'perfil': getattr(solicitud.cliente, 'perfil_cliente', None),
        'otras': Solicitud.objects.filter(cliente=solicitud.cliente).exclude(pk=solicitud.pk).select_related('estado')[:5],
        'form_estado': form_estado,
        'form_cotizacion': form_cotizacion,
        'form_gestion': form_gestion,
        'accion': accion,
    }
    if requerimiento:
        contexto.update({
            'objetivos': nombres_objetivos(requerimiento.objetivos),
            'funcionalidades': nombres_funcionalidades(requerimiento.funcionalidades),
            'integraciones': nombres_integraciones(requerimiento.integraciones),
        })
    return render(request, 'plataforma/panel/solicitud.html', contexto)


def _cotizacion_sugerida(solicitud):
    estimacion = getattr(solicitud, 'estimacion', None)
    sugerencia = {'validez_dias': 15}
    if estimacion:
        sugerencia['monto'] = estimacion.total
        sugerencia['plazo_dias'] = estimacion.semanas_maximas * 5
    elif solicitud.servicio and solicitud.servicio.precio_base:
        sugerencia['monto'] = solicitud.servicio.precio_base
    return sugerencia


@staff_verificado
def panel_servicios(request):
    return render(request, 'plataforma/panel/servicios.html', {
        'seccion': 'servicios',
        'servicios': Servicio.objects.select_related('categoria').annotate(total_solicitudes=Count('solicitudes')),
        'categorias': Categoria.objects.annotate(total_servicios=Count('servicios')),
    })


@staff_verificado
def panel_servicio_form(request, pk=None):
    servicio = get_object_or_404(Servicio, pk=pk) if pk else None
    form = ServicioForm(request.POST or None, instance=servicio)
    if request.method == 'POST' and form.is_valid():
        guardado = form.save()
        messages.success(request, f'Servicio «{guardado.nombre}» guardado.')
        return redirect('panel_servicios')
    return render(request, 'plataforma/panel/formulario.html', {
        'seccion': 'servicios',
        'form': form,
        'titulo': 'Editar servicio' if servicio else 'Nuevo servicio',
        'volver': 'panel_servicios',
    })


@staff_verificado
@require_POST
def panel_servicio_estado(request, pk):
    servicio = get_object_or_404(Servicio, pk=pk)
    servicio.activo = not servicio.activo
    servicio.save(update_fields=['activo', 'fecha_actualizacion'])
    estado = 'activado' if servicio.activo else 'desactivado'
    messages.success(request, f'Servicio «{servicio.nombre}» {estado}.')
    return redirect('panel_servicios')


@staff_verificado
def panel_categoria_form(request, pk=None):
    categoria = get_object_or_404(Categoria, pk=pk) if pk else None
    form = CategoriaForm(request.POST or None, instance=categoria)
    if request.method == 'POST' and form.is_valid():
        guardada = form.save()
        messages.success(request, f'Categoría «{guardada.nombre}» guardada.')
        return redirect('panel_servicios')
    return render(request, 'plataforma/panel/formulario.html', {
        'seccion': 'servicios',
        'form': form,
        'titulo': 'Editar categoría' if categoria else 'Nueva categoría',
        'volver': 'panel_servicios',
    })


@staff_verificado
@require_POST
def panel_categoria_estado(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    categoria.activa = not categoria.activa
    categoria.save(update_fields=['activa'])
    estado = 'activada' if categoria.activa else 'desactivada'
    messages.success(request, f'Categoría «{categoria.nombre}» {estado}.')
    return redirect('panel_servicios')


@staff_verificado
def panel_clientes(request):
    clientes = User.objects.filter(is_staff=False).select_related('perfil_cliente').annotate(
        total=Count('solicitudes'),
        activas=Count('solicitudes', filter=Q(solicitudes__estado__es_final=False)),
    ).order_by('-date_joined')
    busqueda = request.GET.get('q', '').strip()
    if busqueda:
        clientes = clientes.filter(
            Q(email__icontains=busqueda)
            | Q(first_name__icontains=busqueda)
            | Q(last_name__icontains=busqueda)
            | Q(perfil_cliente__empresa__icontains=busqueda)
        )
    pagina = Paginator(clientes, 20).get_page(request.GET.get('pagina'))
    return render(request, 'plataforma/panel/clientes.html', {
        'seccion': 'clientes',
        'pagina': pagina,
        'busqueda': busqueda,
    })


@staff_verificado
def panel_consultas(request):
    mensajes = MensajeAsistente.objects.select_related('usuario').filter(es_asistente=False).order_by('-fecha')
    intenciones = [
        {'nombre': ETIQUETAS_INTENCION.get(fila['intencion'], fila['intencion']), 'cantidad': fila['cantidad']}
        for fila in MensajeAsistente.objects.filter(es_asistente=True)
        .exclude(intencion='')
        .order_by()
        .values('intencion')
        .annotate(cantidad=Count('pk'))
        .order_by('-cantidad')[:8]
    ]
    pagina = Paginator(mensajes, 25).get_page(request.GET.get('pagina'))
    return render(request, 'plataforma/panel/consultas.html', {
        'seccion': 'consultas',
        'pagina': pagina,
        'intenciones': intenciones,
        'max_intencion': max([i['cantidad'] for i in intenciones] + [1]),
    })
