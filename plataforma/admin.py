from django.contrib import admin

from .models import (
    Categoria,
    CodigoVerificacion,
    Cotizacion,
    EstadoSolicitud,
    Estimacion,
    HistorialSolicitud,
    MensajeAsistente,
    PerfilCliente,
    RequerimientoWeb,
    Servicio,
    Solicitud,
)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'orden', 'activa']
    list_editable = ['orden', 'activa']
    search_fields = ['nombre']


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'categoria', 'precio_base', 'destacado', 'activo']
    list_filter = ['tipo', 'activo', 'destacado', 'categoria']
    search_fields = ['nombre', 'resumen', 'descripcion']
    prepopulated_fields = {'slug': ('nombre',)}


@admin.register(PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'empresa', 'telefono', 'ciudad', 'fecha_registro']
    search_fields = ['usuario__email', 'usuario__first_name', 'usuario__last_name', 'empresa']


@admin.register(EstadoSolicitud)
class EstadoSolicitudAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'codigo', 'orden', 'es_final']
    ordering = ['orden']


@admin.register(RequerimientoWeb)
class RequerimientoWebAdmin(admin.ModelAdmin):
    list_display = ['nombre_negocio', 'tipo_sitio', 'complejidad', 'num_paginas', 'fecha_creacion']
    list_filter = ['tipo_sitio', 'complejidad']
    search_fields = ['nombre_negocio']


class HistorialInline(admin.TabularInline):
    model = HistorialSolicitud
    extra = 0
    can_delete = False
    readonly_fields = ['estado_anterior', 'estado_nuevo', 'comentario', 'usuario', 'fecha']


@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    list_display = ['numero', 'titulo', 'cliente', 'tipo', 'estado', 'prioridad', 'fecha_solicitud']
    list_filter = ['tipo', 'estado', 'prioridad']
    search_fields = ['numero', 'titulo', 'cliente__email']
    readonly_fields = ['numero', 'fecha_solicitud', 'fecha_actualizacion']
    inlines = [HistorialInline]


@admin.register(Estimacion)
class EstimacionAdmin(admin.ModelAdmin):
    list_display = ['solicitud', 'total', 'monto_minimo', 'monto_maximo', 'fecha_calculo']
    readonly_fields = ['fecha_calculo']


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ['solicitud', 'monto', 'plazo_dias', 'respuesta_cliente', 'fecha_emision']
    list_filter = ['respuesta_cliente']


@admin.register(HistorialSolicitud)
class HistorialSolicitudAdmin(admin.ModelAdmin):
    list_display = ['solicitud', 'estado_anterior', 'estado_nuevo', 'usuario', 'fecha']
    readonly_fields = ['solicitud', 'estado_anterior', 'estado_nuevo', 'comentario', 'usuario', 'fecha']


@admin.register(MensajeAsistente)
class MensajeAsistenteAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'usuario', 'es_asistente', 'intencion', 'contenido']
    list_filter = ['es_asistente', 'intencion']
    search_fields = ['contenido']


@admin.register(CodigoVerificacion)
class CodigoVerificacionAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'creado', 'expira', 'intentos', 'usado']
    readonly_fields = ['usuario', 'codigo_hash', 'creado', 'expira', 'intentos', 'usado']
