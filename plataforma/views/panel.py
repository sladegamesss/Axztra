"""
Panel del equipo (actor Administrador).

Todas estas vistas exigen una cuenta del equipo con la verificación en dos pasos completada.
Casos de uso: CU15 Gestionar solicitudes, CU16 Emitir cotización definitiva, CU17 Actualizar estado,
CU18 Gestionar servicios y categorías, CU19 Gestionar contenido del sitio y CU20 Consultar indicadores y reportes.
La gestión de una solicitud sigue el diagrama de actividades DA-03 del informe.
"""

import csv
import json
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .. import auditoria, gestion
from ..decoradores import requiere_permiso, staff_verificado
from ..estimacion import nombres_funcionalidades, nombres_integraciones, nombres_objetivos
from ..forms import (
    AdjuntoForm,
    CambioEstadoForm,
    CategoriaForm,
    ConfiguracionSitioForm,
    CotizacionForm,
    GestionInternaForm,
    ItemsCotizacionFormSet,
    MensajeForm,
    PreguntaFrecuenteForm,
    ServicioForm,
)
from ..models import (
    Categoria,
    ConfiguracionSitio,
    Cotizacion,
    EstadoSolicitud,
    Estimacion,
    MensajeAsistente,
    PreguntaFrecuente,
    RegistroActividad,
    Servicio,
    Solicitud,
)

User = get_user_model()

ETIQUETAS_INTENCION = {
    'saludo': 'Saludos',
    'agradecimiento': 'Agradecimientos',
    'creacion': 'Crear un sitio',
    'tienda': 'Tiendas online',
    'estimacion': 'Precios',
    'servicio': 'Precio de un servicio',
    'ideas': 'Ideas por rubro',
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
    'aplicacion': 'Aplicaciones móviles',
    'pregunta_frecuente': 'Preguntas frecuentes',
    'no_entendido': 'No reconocidas',
    'vacio': 'Mensajes vacíos',
}

MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']


# Primer día del mes de una fecha.
def _inicio_mes(fecha):
    return fecha.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


# Resta meses a una fecha (para el gráfico de los últimos 6 meses).
def _restar_meses(fecha, cantidad):
    anio, mes = fecha.year, fecha.month - cantidad
    while mes <= 0:
        mes += 12
        anio -= 1
    return fecha.replace(year=anio, month=mes)


# CU20: resumen con indicadores, gráficos y solicitudes que requieren atención.
@staff_verificado
def panel_inicio(request):
    ahora = timezone.localtime()
    inicio_mes = _inicio_mes(ahora)
    desde_grafico = _restar_meses(inicio_mes, 5)
    hace_30 = ahora - timedelta(days=30)

    resumen = Solicitud.objects.aggregate(
        total=Count('pk'),
        abiertas=Count('pk', filter=Q(estado__es_final=False)),
        nuevas_mes=Count('pk', filter=Q(fecha_solicitud__gte=inicio_mes)),
        por_atender=Count('pk', filter=Q(estado__codigo=EstadoSolicitud.RECIBIDA)),
        sin_asignar=Count('pk', filter=Q(estado__es_final=False, responsable__isnull=True)),
        mias=Count('pk', filter=Q(estado__es_final=False, responsable=request.user)),
    )
    atrasadas = Solicitud.objects.filter(Solicitud.filtro_atrasadas())
    cotizaciones = Cotizacion.objects.aggregate(
        aceptadas=Count('pk', filter=Q(respuesta_cliente='aceptada')),
        respondidas=Count('pk', filter=~Q(respuesta_cliente='')),
        monto_aceptado=Sum('monto', filter=Q(respuesta_cliente='aceptada')),
    )
    tasa = round(cotizaciones['aceptadas'] * 100 / cotizaciones['respondidas']) if cotizaciones['respondidas'] else None
    respuesta_media = Solicitud.objects.filter(
        fecha_primera_respuesta__isnull=False, fecha_solicitud__gte=hace_30
    ).aggregate(
        media=Avg(ExpressionWrapper(F('fecha_primera_respuesta') - F('fecha_solicitud'), output_field=DurationField()))
    )['media']

    por_estado = list(EstadoSolicitud.objects.annotate(cantidad=Count('solicitudes')).order_by('orden'))
    conteo_tipos = dict(Solicitud.objects.order_by().values_list('tipo').annotate(c=Count('pk')))
    por_tipo = [{'clave': clave, 'nombre': nombre, 'cantidad': conteo_tipos.get(clave, 0)} for clave, nombre in Solicitud.TIPOS]

    por_mes = {
        timezone.localtime(fila['mes']).strftime('%Y-%m') if timezone.is_aware(fila['mes']) else fila['mes'].strftime('%Y-%m'): fila['cantidad']
        for fila in Solicitud.objects.filter(fecha_solicitud__gte=desde_grafico)
        .annotate(mes=TruncMonth('fecha_solicitud'))
        .order_by()
        .values('mes')
        .annotate(cantidad=Count('pk'))
    }
    meses = []
    for indice in range(6):
        fecha = _restar_meses(inicio_mes, 5 - indice)
        meses.append({'etiqueta': MESES[fecha.month - 1], 'cantidad': por_mes.get(fecha.strftime('%Y-%m'), 0)})
    maximo_mes = max([m['cantidad'] for m in meses] + [1])
    for mes in meses:
        mes['alto'] = round(mes['cantidad'] * 100 / maximo_mes)

    mensajes_pendientes = (
        Solicitud.objects.filter(mensajes__es_equipo=False, mensajes__leido=False)
        .annotate(no_leidos=Count('mensajes', filter=Q(mensajes__es_equipo=False, mensajes__leido=False)))
        .select_related('cliente', 'estado')
        .order_by('-fecha_actualizacion')[:5]
    )

    return render(request, 'plataforma/panel/inicio.html', {
        'seccion': 'inicio',
        'resumen': resumen,
        'total_atrasadas': atrasadas.count(),
        'atrasadas': atrasadas.select_related('cliente', 'estado', 'responsable').order_by('fecha_solicitud')[:5],
        'clientes': User.objects.filter(is_staff=False, is_active=True).count(),
        'clientes_mes': User.objects.filter(is_staff=False, date_joined__gte=inicio_mes).count(),
        'monto_aceptado': cotizaciones['monto_aceptado'] or 0,
        'tasa_aceptacion': tasa,
        'monto_en_estimacion': Estimacion.objects.filter(solicitud__estado__es_final=False).aggregate(s=Sum('total'))['s'] or 0,
        'respuesta_media_horas': round(respuesta_media.total_seconds() / 3600, 1) if respuesta_media else None,
        'consultas': MensajeAsistente.objects.filter(es_asistente=False, fecha__gte=hace_30).count(),
        'por_estado': por_estado,
        'max_estado': max([e.cantidad for e in por_estado] + [1]),
        'por_tipo': por_tipo,
        'max_tipo': max([t['cantidad'] for t in por_tipo] + [1]),
        'meses': meses,
        'recientes': Solicitud.objects.select_related('estado', 'cliente', 'responsable')[:8],
        'mensajes_pendientes': mensajes_pendientes,
    })


# Aplica los filtros del listado (estado, tipo, prioridad, responsable, búsqueda).
def _filtrar_solicitudes(request, consulta):
    filtros = {
        'estado': request.GET.get('estado', ''),
        'tipo': request.GET.get('tipo', ''),
        'prioridad': request.GET.get('prioridad', ''),
        'responsable': request.GET.get('responsable', ''),
        'q': request.GET.get('q', '').strip()[:80],
        'atrasadas': request.GET.get('atrasadas', ''),
    }
    if filtros['estado'] == 'abiertas':
        consulta = consulta.filter(estado__es_final=False)
    elif filtros['estado']:
        consulta = consulta.filter(estado__codigo=filtros['estado'])
    if filtros['tipo'] in dict(Solicitud.TIPOS):
        consulta = consulta.filter(tipo=filtros['tipo'])
    if filtros['prioridad'] in dict(Solicitud.PRIORIDADES):
        consulta = consulta.filter(prioridad=filtros['prioridad'])
    if filtros['responsable'] == 'mias':
        consulta = consulta.filter(responsable=request.user)
    elif filtros['responsable'] == 'sin':
        consulta = consulta.filter(responsable__isnull=True)
    elif filtros['responsable'].isdigit():
        consulta = consulta.filter(responsable_id=int(filtros['responsable']))
    if filtros['atrasadas']:
        consulta = consulta.filter(Solicitud.filtro_atrasadas())
    if filtros['q']:
        q = filtros['q']
        consulta = consulta.filter(
            Q(numero__icontains=q)
            | Q(titulo__icontains=q)
            | Q(cliente__email__icontains=q)
            | Q(cliente__first_name__icontains=q)
            | Q(cliente__last_name__icontains=q)
            | Q(cliente__perfil_cliente__empresa__icontains=q)
        )
    return consulta, filtros


# Objeto auxiliar para escribir el CSV fila por fila sin cargarlo entero en memoria.
class _Eco:
    def write(self, valor):
        return valor


# Respuesta CSV compatible con Excel (separador ; y codificación UTF-8 con BOM).
def _csv(nombre, encabezados, filas):
    escritor = csv.writer(_Eco(), delimiter=';')

    def generar():
        yield '\ufeff'
        yield escritor.writerow(encabezados)
        for fila in filas:
            yield escritor.writerow(fila)

    respuesta = StreamingHttpResponse(generar(), content_type='text/csv; charset=utf-8')
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre}"'
    return respuesta


# Usuarios del equipo para asignar como responsables.
def _equipo():
    return User.objects.filter(is_staff=True, is_active=True).order_by('first_name', 'email')


# CU15 Gestionar solicitudes: listado con filtros y exportación a CSV.
@staff_verificado
def panel_solicitudes(request):
    consulta = Solicitud.objects.select_related('estado', 'cliente', 'responsable', 'estimacion').annotate(
        no_leidos=Count('mensajes', filter=Q(mensajes__es_equipo=False, mensajes__leido=False))
    ).order_by('-fecha_solicitud', '-pk')
    consulta, filtros = _filtrar_solicitudes(request, consulta)

    if request.GET.get('exportar') == 'csv':
        auditoria.registrar(request, 'exportacion', 'Exportación de solicitudes a CSV')
        filas = (
            [
                s.numero,
                s.titulo,
                s.get_tipo_display(),
                s.estado.nombre,
                s.get_prioridad_display(),
                s.cliente.get_full_name(),
                s.cliente.email,
                (s.responsable.get_full_name() or s.responsable.email) if s.responsable_id else '',
                s.estimacion.total if hasattr(s, 'estimacion') else '',
                timezone.localtime(s.fecha_solicitud).strftime('%d-%m-%Y %H:%M'),
                timezone.localtime(s.fecha_actualizacion).strftime('%d-%m-%Y %H:%M'),
            ]
            for s in consulta.iterator(chunk_size=500)
        )
        return _csv(
            f'solicitudes-{timezone.localdate():%Y%m%d}.csv',
            ['Número', 'Título', 'Tipo', 'Estado', 'Prioridad', 'Cliente', 'Correo', 'Responsable', 'Estimación CLP', 'Ingreso', 'Última actualización'],
            filas,
        )

    pagina = Paginator(consulta, 20).get_page(request.GET.get('pagina'))
    return render(request, 'plataforma/panel/solicitudes.html', {
        'seccion': 'solicitudes',
        'pagina': pagina,
        'estados': EstadoSolicitud.objects.all(),
        'tipos': Solicitud.TIPOS,
        'prioridades': Solicitud.PRIORIDADES,
        'equipo': _equipo(),
        'filtros': filtros,
        'hay_filtros': any(filtros.values()),
    })


# Tablero por etapas: las solicitudes se mueven arrastrando las tarjetas.
@staff_verificado
def panel_tablero(request):
    consulta = Solicitud.objects.select_related('estado', 'cliente', 'responsable').exclude(estado__es_final=True)
    consulta, filtros = _filtrar_solicitudes(request, consulta)
    columnas = []
    for estado in EstadoSolicitud.objects.filter(es_final=False).order_by('orden'):
        tarjetas = consulta.filter(estado=estado).order_by('-fecha_actualizacion')
        columnas.append({'estado': estado, 'total': tarjetas.count(), 'tarjetas': list(tarjetas[:40])})
    return render(request, 'plataforma/panel/tablero.html', {
        'seccion': 'tablero',
        'columnas': columnas,
        'tipos': Solicitud.TIPOS,
        'equipo': _equipo(),
        'filtros': filtros,
    })


# CU17: cambio de estado desde el tablero (lo llama static/js/panel.js).
@staff_verificado
@require_POST
def panel_mover_solicitud(request, pk):
    solicitud = get_object_or_404(Solicitud.objects.select_related('estado', 'cliente'), pk=pk)
    try:
        datos = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'Solicitud no válida.'}, status=400)
    estado = EstadoSolicitud.objects.filter(codigo=datos.get('estado')).first()
    if estado is None:
        return JsonResponse({'error': 'El estado indicado no existe.'}, status=400)
    error = gestion.validar_transicion(solicitud, estado)
    if error:
        return JsonResponse({'error': error}, status=400)
    gestion.cambiar_estado(solicitud, estado, request.user, 'Cambio realizado desde el tablero.', True, request)
    return JsonResponse({'ok': True, 'estado': estado.codigo, 'nombre': estado.nombre})


# Ítems con los que parte la cotización (los de la versión anterior o los de la estimación).
def _items_iniciales(solicitud, cotizacion):
    if cotizacion is not None:
        return [
            {'descripcion': item['descripcion'], 'cantidad': item['cantidad'], 'precio_unitario': item['precio_unitario']}
            for item in cotizacion.lineas
        ]
    estimacion = getattr(solicitud, 'estimacion', None)
    if estimacion and estimacion.desglose:
        return [{'descripcion': linea['concepto'], 'cantidad': 1, 'precio_unitario': linea['monto']} for linea in estimacion.desglose]
    if solicitud.servicio_id and solicitud.servicio.precio_base:
        return [{'descripcion': solicitud.servicio.nombre, 'cantidad': 1, 'precio_unitario': solicitud.servicio.precio_base}]
    return [{'descripcion': solicitud.titulo, 'cantidad': 1, 'precio_unitario': 0}]


# Datos iniciales del formulario de cotización.
def _cotizacion_inicial(solicitud):
    estimacion = getattr(solicitud, 'estimacion', None)
    inicial = {'validez_dias': 15, 'plazo_dias': 10}
    if estimacion:
        inicial['plazo_dias'] = estimacion.semanas_maximas * 5
    return inicial


# Ficha de una solicitud (CU15). Desde aquí se:
# actualiza el estado (CU17), se emite la cotización (CU16), se asigna responsable,
# se conversa con el cliente (CU13) y se suben archivos (CU10).
@staff_verificado
def panel_solicitud(request, pk):
    solicitud = get_object_or_404(
        Solicitud.objects.select_related('estado', 'cliente', 'servicio', 'requerimiento', 'responsable', 'relacionada'), pk=pk
    )
    cotizacion = getattr(solicitud, 'cotizacion', None)
    accion = request.POST.get('accion') if request.method == 'POST' else None

    form_estado = CambioEstadoForm(solicitud=solicitud)
    form_cotizacion = CotizacionForm(instance=cotizacion, initial=None if cotizacion else _cotizacion_inicial(solicitud))
    items = ItemsCotizacionFormSet(prefix='items', initial=_items_iniciales(solicitud, cotizacion))
    form_gestion = GestionInternaForm(instance=solicitud)
    form_mensaje = MensajeForm()
    form_adjunto = AdjuntoForm()

    if accion == 'estado':
        form_estado = CambioEstadoForm(request.POST, solicitud=solicitud)
        if form_estado.is_valid():
            datos = form_estado.cleaned_data
            gestion.cambiar_estado(solicitud, datos['estado'], request.user, datos['comentario'], datos['notificar'], request)
            messages.success(request, f"Estado actualizado a {datos['estado'].nombre}.")
            return redirect('panel_solicitud', pk=solicitud.pk)
    elif accion == 'cotizacion':
        if solicitud.estado.es_final and solicitud.estado.codigo != EstadoSolicitud.RECHAZADA:
            messages.error(request, 'No se puede cotizar una solicitud cerrada.')
            return redirect('panel_solicitud', pk=solicitud.pk)
        form_cotizacion = CotizacionForm(request.POST, instance=cotizacion or Cotizacion(solicitud=solicitud))
        items = ItemsCotizacionFormSet(request.POST, prefix='items')
        if form_cotizacion.is_valid() and items.is_valid():
            gestion.emitir_cotizacion(solicitud, form_cotizacion.save(commit=False), items.items(), request.user, request)
            messages.success(request, 'Cotización emitida y enviada al cliente.')
            return redirect('panel_solicitud', pk=solicitud.pk)
    elif accion == 'gestion':
        responsable_anterior_id = solicitud.responsable_id
        form_gestion = GestionInternaForm(request.POST, instance=solicitud)
        if form_gestion.is_valid():
            datos = form_gestion.cleaned_data
            solicitud.responsable_id = responsable_anterior_id
            solicitud.prioridad = datos['prioridad']
            solicitud.notas_internas = datos['notas_internas']
            solicitud.save(update_fields=['prioridad', 'notas_internas', 'fecha_actualizacion'])
            gestion.asignar_responsable(solicitud, datos['responsable'], request.user, request)
            auditoria.registrar(request, 'gestion', f'{solicitud.numero}: datos internos actualizados', solicitud)
            messages.success(request, 'Datos internos guardados.')
            return redirect('panel_solicitud', pk=solicitud.pk)
    elif accion == 'mensaje':
        form_mensaje = MensajeForm(request.POST)
        if form_mensaje.is_valid():
            gestion.enviar_mensaje(solicitud, request.user, form_mensaje.cleaned_data['texto'], request)
            messages.success(request, 'Mensaje enviado al cliente.')
            return redirect(f"{request.path}#mensajes")
    elif accion == 'adjunto':
        form_adjunto = AdjuntoForm(request.POST, request.FILES)
        if form_adjunto.is_valid():
            gestion.guardar_adjunto(solicitud, form_adjunto.cleaned_data['archivo'], request.user, es_equipo=True, request=request)
            messages.success(request, 'Archivo adjuntado a la solicitud.')
            return redirect(f"{request.path}#archivos")

    gestion.marcar_mensajes_leidos(solicitud, request.user)
    requerimiento = solicitud.requerimiento
    contexto = {
        'seccion': 'solicitudes',
        'solicitud': solicitud,
        'cotizacion': cotizacion,
        'estimacion': getattr(solicitud, 'estimacion', None),
        'historial': solicitud.historial.select_related('estado_nuevo', 'estado_anterior', 'usuario'),
        'mensajes_solicitud': solicitud.mensajes.select_related('autor'),
        'adjuntos': solicitud.adjuntos.select_related('subido_por'),
        'perfil': getattr(solicitud.cliente, 'perfil_cliente', None),
        'otras': Solicitud.objects.filter(cliente=solicitud.cliente).exclude(pk=solicitud.pk).select_related('estado')[:6],
        'form_estado': form_estado,
        'form_cotizacion': form_cotizacion,
        'items': items,
        'form_gestion': form_gestion,
        'form_mensaje': form_mensaje,
        'form_adjunto': form_adjunto,
        'accion': accion,
        'iva': settings.AXZTRA['IVA'],
    }
    if requerimiento:
        contexto.update({
            'objetivos': nombres_objetivos(requerimiento.objetivos),
            'funcionalidades': nombres_funcionalidades(requerimiento.funcionalidades),
            'integraciones': nombres_integraciones(requerimiento.integraciones),
        })
    return render(request, 'plataforma/panel/solicitud.html', contexto)


# CU18: listado de servicios y categorías.
@requiere_permiso('plataforma.change_servicio')
def panel_servicios(request):
    return render(request, 'plataforma/panel/servicios.html', {
        'seccion': 'servicios',
        'servicios': Servicio.objects.select_related('categoria').annotate(total_solicitudes=Count('solicitudes')),
        'categorias': Categoria.objects.annotate(total_servicios=Count('servicios')),
    })


# CU18: crear o editar un servicio.
@requiere_permiso('plataforma.change_servicio')
def panel_servicio_form(request, pk=None):
    servicio = get_object_or_404(Servicio, pk=pk) if pk else None
    form = ServicioForm(request.POST or None, instance=servicio)
    if request.method == 'POST' and form.is_valid():
        guardado = form.save()
        auditoria.registrar(request, 'servicio', f'Servicio "{guardado.nombre}" {"editado" if servicio else "creado"}')
        messages.success(request, f'Servicio "{guardado.nombre}" guardado.')
        return redirect('panel_servicios')
    return render(request, 'plataforma/panel/formulario.html', {
        'seccion': 'servicios',
        'form': form,
        'titulo': 'Editar servicio' if servicio else 'Nuevo servicio',
        'volver': 'panel_servicios',
        'volver_texto': 'Servicios y categorías',
    })


# CU18: publicar u ocultar un servicio.
@requiere_permiso('plataforma.change_servicio')
@require_POST
def panel_servicio_estado(request, pk):
    servicio = get_object_or_404(Servicio, pk=pk)
    servicio.activo = not servicio.activo
    servicio.save(update_fields=['activo', 'fecha_actualizacion'])
    estado = 'activado' if servicio.activo else 'desactivado'
    auditoria.registrar(request, 'servicio', f'Servicio "{servicio.nombre}" {estado}')
    messages.success(request, f'Servicio "{servicio.nombre}" {estado}.')
    return redirect('panel_servicios')


# CU18: crear o editar una categoría.
@requiere_permiso('plataforma.change_categoria')
def panel_categoria_form(request, pk=None):
    categoria = get_object_or_404(Categoria, pk=pk) if pk else None
    form = CategoriaForm(request.POST or None, instance=categoria)
    if request.method == 'POST' and form.is_valid():
        guardada = form.save()
        auditoria.registrar(request, 'servicio', f'Categoría "{guardada.nombre}" {"editada" if categoria else "creada"}')
        messages.success(request, f'Categoría "{guardada.nombre}" guardada.')
        return redirect('panel_servicios')
    return render(request, 'plataforma/panel/formulario.html', {
        'seccion': 'servicios',
        'form': form,
        'titulo': 'Editar categoría' if categoria else 'Nueva categoría',
        'volver': 'panel_servicios',
        'volver_texto': 'Servicios y categorías',
    })


# CU18: activar o desactivar una categoría.
@requiere_permiso('plataforma.change_categoria')
@require_POST
def panel_categoria_estado(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    categoria.activa = not categoria.activa
    categoria.save(update_fields=['activa'])
    estado = 'activada' if categoria.activa else 'desactivada'
    auditoria.registrar(request, 'servicio', f'Categoría "{categoria.nombre}" {estado}')
    messages.success(request, f'Categoría "{categoria.nombre}" {estado}.')
    return redirect('panel_servicios')


# CU19 Gestionar contenido del sitio: datos de contacto, aviso y preguntas frecuentes.
@requiere_permiso('plataforma.change_preguntafrecuente')
def panel_contenido(request):
    configuracion = ConfiguracionSitio.actual()
    form_configuracion = ConfiguracionSitioForm(instance=configuracion)
    if request.method == 'POST':
        if not request.user.has_perm('plataforma.change_configuracionsitio'):
            messages.error(request, 'Tu cuenta no puede modificar los datos de contacto.')
            return redirect('panel_contenido')
        form_configuracion = ConfiguracionSitioForm(request.POST, instance=configuracion)
        if form_configuracion.is_valid():
            form_configuracion.save()
            auditoria.registrar(request, 'contenido', 'Datos de contacto del sitio actualizados')
            messages.success(request, 'Datos del sitio actualizados.')
            return redirect('panel_contenido')
    return render(request, 'plataforma/panel/contenido.html', {
        'seccion': 'contenido',
        'preguntas': PreguntaFrecuente.objects.all(),
        'form_configuracion': form_configuracion,
        'puede_configurar': request.user.has_perm('plataforma.change_configuracionsitio'),
    })


# CU19: crear o editar una pregunta frecuente.
@requiere_permiso('plataforma.change_preguntafrecuente')
def panel_pregunta_form(request, pk=None):
    pregunta = get_object_or_404(PreguntaFrecuente, pk=pk) if pk else None
    form = PreguntaFrecuenteForm(request.POST or None, instance=pregunta)
    if request.method == 'POST' and form.is_valid():
        guardada = form.save()
        auditoria.registrar(request, 'contenido', f'Pregunta frecuente "{guardada.pregunta[:80]}" guardada')
        messages.success(request, 'Pregunta frecuente guardada.')
        return redirect('panel_contenido')
    return render(request, 'plataforma/panel/formulario.html', {
        'seccion': 'contenido',
        'form': form,
        'titulo': 'Editar pregunta frecuente' if pregunta else 'Nueva pregunta frecuente',
        'volver': 'panel_contenido',
        'volver_texto': 'Contenido del sitio',
    })


# CU19: publicar u ocultar una pregunta frecuente.
@requiere_permiso('plataforma.change_preguntafrecuente')
@require_POST
def panel_pregunta_estado(request, pk):
    pregunta = get_object_or_404(PreguntaFrecuente, pk=pk)
    pregunta.activa = not pregunta.activa
    pregunta.save(update_fields=['activa', 'fecha_actualizacion'])
    messages.success(request, 'Pregunta publicada.' if pregunta.activa else 'Pregunta ocultada.')
    return redirect('panel_contenido')


# Listado de clientes con exportación a CSV.
@staff_verificado
def panel_clientes(request):
    clientes = User.objects.filter(is_staff=False).select_related('perfil_cliente').annotate(
        total=Count('solicitudes', distinct=True),
        activas=Count('solicitudes', filter=Q(solicitudes__estado__es_final=False), distinct=True),
    ).order_by('-date_joined')
    busqueda = request.GET.get('q', '').strip()[:80]
    if busqueda:
        clientes = clientes.filter(
            Q(email__icontains=busqueda)
            | Q(first_name__icontains=busqueda)
            | Q(last_name__icontains=busqueda)
            | Q(perfil_cliente__empresa__icontains=busqueda)
        )
    if request.GET.get('exportar') == 'csv':
        auditoria.registrar(request, 'exportacion', 'Exportación de clientes a CSV')
        filas = (
            [
                c.get_full_name(),
                c.email,
                getattr(getattr(c, 'perfil_cliente', None), 'empresa', ''),
                getattr(getattr(c, 'perfil_cliente', None), 'telefono', ''),
                getattr(getattr(c, 'perfil_cliente', None), 'ciudad', ''),
                c.total,
                c.activas,
                timezone.localtime(c.date_joined).strftime('%d-%m-%Y'),
                'Sí' if c.is_active else 'No',
            ]
            for c in clientes.iterator(chunk_size=500)
        )
        return _csv(
            f'clientes-{timezone.localdate():%Y%m%d}.csv',
            ['Nombre', 'Correo', 'Empresa', 'Teléfono', 'Ciudad', 'Solicitudes', 'En curso', 'Registro', 'Activo'],
            filas,
        )
    pagina = Paginator(clientes, 25).get_page(request.GET.get('pagina'))
    return render(request, 'plataforma/panel/clientes.html', {
        'seccion': 'clientes',
        'pagina': pagina,
        'busqueda': busqueda,
    })


# Conversaciones de los clientes con el asistente virtual.
@staff_verificado
def panel_consultas(request):
    mensajes_usuario = MensajeAsistente.objects.select_related('usuario').filter(es_asistente=False).order_by('-fecha')
    intenciones = [
        {'nombre': ETIQUETAS_INTENCION.get(fila['intencion'], fila['intencion']), 'cantidad': fila['cantidad']}
        for fila in MensajeAsistente.objects.filter(es_asistente=True)
        .exclude(intencion='')
        .order_by()
        .values('intencion')
        .annotate(cantidad=Count('pk'))
        .order_by('-cantidad')[:10]
    ]
    no_reconocidas = MensajeAsistente.objects.filter(es_asistente=True, intencion='no_entendido').count()
    pagina = Paginator(mensajes_usuario, 25).get_page(request.GET.get('pagina'))
    return render(request, 'plataforma/panel/consultas.html', {
        'seccion': 'consultas',
        'pagina': pagina,
        'intenciones': intenciones,
        'max_intencion': max([i['cantidad'] for i in intenciones] + [1]),
        'no_reconocidas': no_reconocidas,
    })


# CU20: registro de actividad (auditoría).
@requiere_permiso('plataforma.view_registroactividad')
def panel_actividad(request):
    registros = RegistroActividad.objects.select_related('usuario', 'solicitud')
    accion = request.GET.get('accion', '')
    if accion in dict(RegistroActividad.ACCIONES):
        registros = registros.filter(accion=accion)
    else:
        accion = ''
    pagina = Paginator(registros, 30).get_page(request.GET.get('pagina'))
    return render(request, 'plataforma/panel/actividad.html', {
        'seccion': 'actividad',
        'pagina': pagina,
        'acciones': RegistroActividad.ACCIONES,
        'accion_activa': accion,
    })
