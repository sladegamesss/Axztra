"""
Administración de datos de Django (menú "Administración de datos" del panel).

Permite ver y corregir directamente las 18 tablas. Para el trabajo diario se usa el panel;
esta sección es para casos especiales. Exige la verificación en dos pasos.
"""

from django.contrib import admin

from .models import (
    Adjunto,
    Categoria,
    CodigoVerificacion,
    ConfiguracionSitio,
    Cotizacion,
    EstadoSolicitud,
    Estimacion,
    HistorialSolicitud,
    MensajeAsistente,
    MensajeSolicitud,
    PerfilCliente,
    PreguntaFrecuente,
    RegistroActividad,
    RequerimientoWeb,
    Servicio,
    Solicitud,
    TokenAPI,
)


# Categorías del catálogo.
@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'orden', 'activa']
    list_editable = ['orden', 'activa']
    search_fields = ['nombre']


# Servicios del catálogo.
@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'categoria', 'precio_base', 'destacado', 'activo']
    list_filter = ['tipo', 'activo', 'destacado', 'categoria']
    search_fields = ['nombre', 'resumen', 'descripcion']
    prepopulated_fields = {'slug': ('nombre',)}


# Perfiles de los clientes.
@admin.register(PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'empresa', 'telefono', 'ciudad', 'fecha_registro']
    search_fields = ['usuario__email', 'usuario__first_name', 'usuario__last_name', 'empresa']
    list_select_related = ['usuario']


# Estados del flujo de atención.
@admin.register(EstadoSolicitud)
class EstadoSolicitudAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'codigo', 'orden', 'color', 'es_final']
    ordering = ['orden']


# Respuestas del formulario de creación de sitios.
@admin.register(RequerimientoWeb)
class RequerimientoWebAdmin(admin.ModelAdmin):
    list_display = ['nombre_negocio', 'tipo_sitio', 'complejidad', 'num_paginas', 'estilo_visual', 'presupuesto', 'fecha_creacion']
    list_filter = ['tipo_sitio', 'complejidad', 'estilo_visual', 'situacion_logo', 'presupuesto']
    search_fields = ['nombre_negocio']


# Historial que se muestra dentro de cada solicitud.
class HistorialInline(admin.TabularInline):
    model = HistorialSolicitud
    extra = 0
    can_delete = False
    readonly_fields = ['estado_anterior', 'estado_nuevo', 'comentario', 'usuario', 'fecha']


# Mensajes que se muestran dentro de cada solicitud.
class MensajeInline(admin.TabularInline):
    model = MensajeSolicitud
    extra = 0
    readonly_fields = ['autor', 'es_equipo', 'texto', 'leido', 'fecha']


# Solicitudes con su historial y mensajes.
@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    list_display = ['numero', 'titulo', 'cliente', 'tipo', 'estado', 'prioridad', 'responsable', 'fecha_solicitud']
    list_filter = ['tipo', 'estado', 'prioridad', 'responsable']
    search_fields = ['numero', 'titulo', 'cliente__email']
    readonly_fields = ['numero', 'token_envio', 'fecha_primera_respuesta', 'fecha_solicitud', 'fecha_actualizacion']
    raw_id_fields = ['cliente', 'relacionada', 'requerimiento']
    list_select_related = ['cliente', 'estado', 'responsable']
    inlines = [HistorialInline, MensajeInline]


# Estimaciones referenciales.
@admin.register(Estimacion)
class EstimacionAdmin(admin.ModelAdmin):
    list_display = ['solicitud', 'total', 'monto_minimo', 'monto_maximo', 'fecha_calculo']
    readonly_fields = ['fecha_calculo']
    list_select_related = ['solicitud']


# Cotizaciones definitivas.
@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ['solicitud', 'version', 'monto', 'plazo_dias', 'respuesta_cliente', 'fecha_emision']
    list_filter = ['respuesta_cliente']
    list_select_related = ['solicitud']


# Historial de cambios de estado.
@admin.register(HistorialSolicitud)
class HistorialSolicitudAdmin(admin.ModelAdmin):
    list_display = ['solicitud', 'estado_anterior', 'estado_nuevo', 'usuario', 'fecha']
    readonly_fields = ['solicitud', 'estado_anterior', 'estado_nuevo', 'comentario', 'usuario', 'fecha']
    list_select_related = ['solicitud', 'estado_anterior', 'estado_nuevo', 'usuario']


# Mensajes entre cliente y equipo.
@admin.register(MensajeSolicitud)
class MensajeSolicitudAdmin(admin.ModelAdmin):
    list_display = ['solicitud', 'autor', 'es_equipo', 'leido', 'fecha']
    list_filter = ['es_equipo', 'leido']
    search_fields = ['texto', 'solicitud__numero']
    list_select_related = ['solicitud', 'autor']


# Archivos adjuntos.
@admin.register(Adjunto)
class AdjuntoAdmin(admin.ModelAdmin):
    list_display = ['nombre_original', 'solicitud', 'tamano', 'subido_por', 'fecha']
    search_fields = ['nombre_original', 'solicitud__numero']
    readonly_fields = ['tamano', 'tipo_contenido', 'fecha']
    list_select_related = ['solicitud', 'subido_por']


# Preguntas frecuentes.
@admin.register(PreguntaFrecuente)
class PreguntaFrecuenteAdmin(admin.ModelAdmin):
    list_display = ['pregunta', 'orden', 'activa']
    list_editable = ['orden', 'activa']
    search_fields = ['pregunta', 'respuesta', 'palabras_clave']


# Configuración del sitio (registro único).
@admin.register(ConfiguracionSitio)
class ConfiguracionSitioAdmin(admin.ModelAdmin):
    list_display = ['correo_contacto', 'whatsapp_visible', 'ubicacion', 'fecha_actualizacion']

    def has_add_permission(self, request):
        return not ConfiguracionSitio.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# Registro de actividad, solo lectura.
@admin.register(RegistroActividad)
class RegistroActividadAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'usuario', 'accion', 'descripcion', 'ip']
    list_filter = ['accion']
    search_fields = ['descripcion', 'usuario__email']
    readonly_fields = ['fecha', 'usuario', 'accion', 'descripcion', 'solicitud', 'ip']
    list_select_related = ['usuario']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# Tokens de la API; desde aquí se pueden desactivar.
@admin.register(TokenAPI)
class TokenAPIAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'prefijo', 'activo', 'creado_por', 'fecha_creacion', 'ultimo_uso']
    list_filter = ['activo']
    readonly_fields = ['prefijo', 'creado_por', 'fecha_creacion', 'ultimo_uso']
    fields = ['nombre', 'activo', 'prefijo', 'creado_por', 'fecha_creacion', 'ultimo_uso']

    def has_add_permission(self, request):
        return False


# Mensajes del asistente virtual.
@admin.register(MensajeAsistente)
class MensajeAsistenteAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'usuario', 'es_asistente', 'intencion', 'contenido']
    list_filter = ['es_asistente', 'intencion']
    search_fields = ['contenido']
    list_select_related = ['usuario']


# Códigos de verificación, solo lectura.
@admin.register(CodigoVerificacion)
class CodigoVerificacionAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'creado', 'expira', 'intentos', 'usado']
    readonly_fields = ['usuario', 'codigo_hash', 'creado', 'expira', 'intentos', 'usado']
