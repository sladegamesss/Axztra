from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from ..estimacion import PRECIO_BASE_POR_TIPO
from ..models import Categoria, Servicio


def inicio(request):
    destacados = Servicio.objects.filter(activo=True, destacado=True).select_related('categoria')[:6]
    if not destacados:
        destacados = Servicio.objects.filter(activo=True).select_related('categoria')[:6]
    return render(request, 'plataforma/inicio.html', {
        'servicios': destacados,
        'precio_landing': PRECIO_BASE_POR_TIPO['landing'],
    })


def catalogo(request):
    servicios = Servicio.objects.filter(activo=True).select_related('categoria')
    categorias = Categoria.objects.filter(activa=True)
    categoria_id = request.GET.get('categoria', '')
    tipo = request.GET.get('tipo', '')
    busqueda = request.GET.get('q', '').strip()

    if categoria_id.isdigit():
        servicios = servicios.filter(categoria_id=int(categoria_id))
    else:
        categoria_id = ''
    if tipo in dict(Servicio.TIPOS):
        servicios = servicios.filter(tipo=tipo)
    else:
        tipo = ''
    if busqueda:
        servicios = servicios.filter(
            Q(nombre__icontains=busqueda) | Q(resumen__icontains=busqueda) | Q(descripcion__icontains=busqueda)
        )

    return render(request, 'plataforma/catalogo.html', {
        'servicios': servicios,
        'categorias': categorias,
        'tipos': Servicio.TIPOS,
        'categoria_activa': categoria_id,
        'tipo_activo': tipo,
        'busqueda': busqueda,
        'hay_filtros': bool(categoria_id or tipo or busqueda),
    })


def servicio_detalle(request, slug):
    servicio = get_object_or_404(Servicio.objects.select_related('categoria'), slug=slug, activo=True)
    relacionados = Servicio.objects.filter(activo=True, tipo=servicio.tipo).exclude(pk=servicio.pk)[:3]
    return render(request, 'plataforma/servicio_detalle.html', {
        'servicio': servicio,
        'relacionados': relacionados,
    })
