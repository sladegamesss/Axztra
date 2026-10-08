"""
Modelo de datos de AXZTRA.

Cada clase de este archivo es una tabla de la base de datos (con el prefijo plataforma_).
Los nombres de clases, tablas y campos son los mismos del Informe Final de Diseño:
diagrama de clases (sección 4.1), modelo relacional (4.2, Tabla 12) y diccionario de datos (4.3, Tablas 13 a 30).
La tabla de usuarios es auth_user, que viene incluida en Django (clase Usuario en el informe).
Si cambias un campo aquí, crea la migración con: python manage.py makemigrations
"""

import hashlib
import os
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import models, transaction
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

CLAVE_CACHE_ESTADOS = 'axztra:estados'
CLAVE_CACHE_CONFIGURACION = 'axztra:configuracion'


# Tabla plataforma_categoria (Tabla 15): agrupa los servicios del catálogo.
class Categoria(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.TextField(blank=True)
    icono = models.CharField(max_length=60, default='fa-solid fa-layer-group')
    orden = models.PositiveIntegerField(default=0)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'categoría'
        verbose_name_plural = 'categorías'

    def __str__(self):
        return self.nombre


# Tabla plataforma_servicio (Tabla 16): servicios que se muestran en el catálogo (RF01, se administran en CU18).
class Servicio(models.Model):
    TIPO_CREACION = 'Creacion'
    TIPO_MEJORA = 'Mejora'
    TIPO_SOPORTE = 'Soporte'
    TIPO_MANTENIMIENTO = 'Mantenimiento'
    TIPOS = [
        (TIPO_CREACION, 'Creación de página web'),
        (TIPO_MEJORA, 'Mejora de página existente'),
        (TIPO_SOPORTE, 'Soporte técnico'),
        (TIPO_MANTENIMIENTO, 'Mantenimiento'),
    ]
    ICONOS_TIPO = {
        TIPO_CREACION: 'fa-solid fa-laptop-code',
        TIPO_MEJORA: 'fa-solid fa-arrow-trend-up',
        TIPO_SOPORTE: 'fa-solid fa-headset',
        TIPO_MANTENIMIENTO: 'fa-solid fa-gear',
    }

    nombre = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    resumen = models.CharField(max_length=180)
    descripcion = models.TextField()
    incluye = models.TextField(blank=True, help_text='Un elemento por línea.')
    tipo = models.CharField(max_length=20, choices=TIPOS)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, related_name='servicios')
    precio_base = models.PositiveIntegerField(default=0, help_text='Valor referencial en CLP. Use 0 para "a cotizar".')
    plazo_referencial = models.CharField(max_length=60, blank=True)
    destacado = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['tipo', 'nombre']
        verbose_name = 'servicio'
        verbose_name_plural = 'servicios'
        constraints = [
            models.UniqueConstraint(Lower('nombre'), name='servicio_nombre_unico'),
            models.CheckConstraint(check=models.Q(tipo__in=['Creacion', 'Mejora', 'Soporte', 'Mantenimiento']), name='servicio_tipo_valido'),
        ]

    def __str__(self):
        return self.nombre

    # Genera el slug (texto de la dirección web) a partir del nombre la primera vez que se guarda.
    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.nombre)[:120] or 'servicio'
            slug = base
            indice = 2
            while Servicio.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{indice}'
                indice += 1
            self.slug = slug
        super().save(*args, **kwargs)

    # Dirección de la ficha pública del servicio.
    def get_absolute_url(self):
        return reverse('servicio_detalle', args=[self.slug])

    # Convierte el campo "incluye" (un ítem por línea) en una lista para mostrarla.
    @property
    def lista_incluye(self):
        return [linea.strip() for linea in self.incluye.splitlines() if linea.strip()]

    # Ícono que se muestra según el tipo de servicio.
    @property
    def icono(self):
        if self.categoria_id and self.categoria.icono:
            return self.categoria.icono
        return self.ICONOS_TIPO.get(self.tipo, 'fa-solid fa-code')

    # Formulario de solicitud que corresponde al tipo de este servicio.
    @property
    def url_solicitud(self):
        rutas = {
            self.TIPO_CREACION: 'crear_web',
            self.TIPO_MEJORA: 'solicitar_mejora',
            self.TIPO_SOPORTE: 'solicitar_soporte',
            self.TIPO_MANTENIMIENTO: 'solicitar_mantenimiento',
        }
        return f"{reverse(rutas[self.tipo])}?servicio={self.pk}"


# Tabla plataforma_perfilcliente (Tabla 14): datos extra del cliente. Relación 1 a 1 con auth_user.
class PerfilCliente(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil_cliente')
    empresa = models.CharField('empresa o emprendimiento', max_length=200, blank=True)
    telefono = models.CharField('teléfono', max_length=20, blank=True)
    rut = models.CharField('RUT', max_length=12, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    recibir_notificaciones = models.BooleanField(default=True)
    fecha_aceptacion_terminos = models.DateTimeField(null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'perfil de cliente'
        verbose_name_plural = 'perfiles de cliente'

    def __str__(self):
        return self.usuario.get_full_name() or self.usuario.email


# Tabla plataforma_estadosolicitud (Tabla 17): etapas del flujo de atención (Recibida, En revisión, Cotizada, etc.).
class EstadoSolicitud(models.Model):
    RECIBIDA = 'recibida'
    EN_REVISION = 'en_revision'
    COTIZADA = 'cotizada'
    APROBADA = 'aprobada'
    EN_DESARROLLO = 'en_desarrollo'
    COMPLETADA = 'completada'
    RECHAZADA = 'rechazada'
    CANCELADA = 'cancelada'
    FLUJO = [RECIBIDA, EN_REVISION, COTIZADA, APROBADA, EN_DESARROLLO, COMPLETADA]

    codigo = models.SlugField(max_length=30, unique=True)
    nombre = models.CharField(max_length=60)
    descripcion = models.CharField(max_length=200, blank=True)
    orden = models.PositiveSmallIntegerField(default=0)
    color = models.CharField(max_length=20, default='azul')
    es_final = models.BooleanField(default=False)

    class Meta:
        ordering = ['orden']
        verbose_name = 'estado de solicitud'
        verbose_name_plural = 'estados de solicitud'

    def __str__(self):
        return self.nombre

    # Lista de estados guardada en caché para no consultarla en cada página.
    @classmethod
    def todos(cls):
        estados = cache.get(CLAVE_CACHE_ESTADOS)
        if estados is None:
            estados = {estado.codigo: estado for estado in cls.objects.all()}
            cache.set(CLAVE_CACHE_ESTADOS, estados, 600)
        return estados

    # Busca un estado por su código, por ejemplo EstadoSolicitud.obtener('cotizada').
    @classmethod
    def obtener(cls, codigo):
        estado = cls.todos().get(codigo)
        if estado is None:
            cache.delete(CLAVE_CACHE_ESTADOS)
            estado = cls.objects.get(codigo=codigo)
        return estado


# Tabla plataforma_requerimientoweb (Tabla 19): respuestas del formulario de cuatro pasos para crear un sitio (CU09).
class RequerimientoWeb(models.Model):
    TIPOS_SITIO = [
        ('landing', 'Landing page'),
        ('corporativo', 'Sitio corporativo o institucional'),
        ('portafolio', 'Portafolio o blog'),
        ('servicios', 'Sitio de servicios con reservas'),
        ('tienda', 'Tienda online'),
    ]
    COMPLEJIDADES = [
        ('basica', 'Básica'),
        ('media', 'Media'),
        ('alta', 'Alta'),
    ]
    ESTILOS = [
        ('sin_preferencia', 'Sin preferencia'),
        ('moderno', 'Moderno'),
        ('minimalista', 'Minimalista'),
        ('elegante', 'Elegante'),
        ('colorido', 'Colorido'),
        ('corporativo', 'Formal o corporativo'),
    ]
    SECCIONES = [
        ('inicio', 'Inicio'),
        ('nosotros', 'Quiénes somos'),
        ('servicios', 'Servicios'),
        ('productos', 'Productos'),
        ('galeria', 'Galería'),
        ('testimonios', 'Testimonios'),
        ('blog', 'Blog o noticias'),
        ('preguntas', 'Preguntas frecuentes'),
        ('reservas', 'Reservas'),
        ('contacto', 'Contacto'),
    ]
    OPCIONES_LOGO = [
        ('tiene', 'Ya tengo logo'),
        ('mejorar', 'Tengo logo, pero quiero mejorarlo'),
        ('crear', 'Necesito un logo nuevo'),
    ]
    PRESUPUESTOS = [
        ('por_definir', 'Aún no lo defino'),
        ('menos_300', 'Menos de $300.000'),
        ('300_600', 'Entre $300.000 y $600.000'),
        ('600_1000', 'Entre $600.000 y $1.000.000'),
        ('mas_1000', 'Más de $1.000.000'),
    ]
    MEDIOS_CONTACTO = [
        ('correo', 'Correo electrónico'),
        ('telefono', 'Llamada telefónica'),
        ('whatsapp', 'WhatsApp'),
    ]

    # Paso 2 del formulario: datos del negocio.
    nombre_negocio = models.CharField(max_length=150)
    rubro = models.CharField(max_length=60)
    descripcion_negocio = models.TextField()
    publico_objetivo = models.CharField(max_length=200, blank=True)
    # Paso 1 del formulario: tipo de sitio y sitio actual.
    tipo_sitio = models.CharField(max_length=20, choices=TIPOS_SITIO)
    tiene_sitio_actual = models.BooleanField(default=False)
    url_sitio_actual = models.URLField(blank=True)
    # Paso 2: objetivos del sitio (lista en JSON).
    objetivos = models.JSONField(default=list, blank=True)
    # Paso 3: alcance y funcionalidades (se usan en la fórmula de estimación).
    num_paginas = models.PositiveSmallIntegerField(default=5)
    complejidad = models.CharField(max_length=10, choices=COMPLEJIDADES, default='media')
    funcionalidades = models.JSONField(default=list, blank=True)
    integraciones = models.JSONField(default=list, blank=True)
    # Paso 4: diseño y detalles (no cambian la estimación, orientan al equipo).
    estilo_visual = models.CharField(max_length=20, choices=ESTILOS, default='sin_preferencia')
    colores = models.CharField(max_length=120, blank=True)
    secciones = models.JSONField(default=list, blank=True)
    situacion_logo = models.CharField(max_length=10, choices=OPCIONES_LOGO, default='tiene')
    tiene_contenido = models.BooleanField(default=False)
    sitios_referencia = models.TextField(blank=True)
    dominio = models.CharField(max_length=120, blank=True)
    presupuesto = models.CharField(max_length=12, choices=PRESUPUESTOS, default='por_definir')
    medio_contacto = models.CharField(max_length=10, choices=MEDIOS_CONTACTO, default='correo')
    observaciones = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'requerimiento web'
        verbose_name_plural = 'requerimientos web'
        constraints = [
            models.CheckConstraint(check=models.Q(num_paginas__gte=1, num_paginas__lte=60), name='requerimiento_paginas_rango'),
            models.CheckConstraint(check=models.Q(complejidad__in=['basica', 'media', 'alta']), name='requerimiento_complejidad_valida'),
            models.CheckConstraint(
                check=models.Q(tipo_sitio__in=['landing', 'corporativo', 'portafolio', 'servicios', 'tienda']),
                name='requerimiento_tipo_sitio_valido',
            ),
            models.CheckConstraint(
                check=models.Q(estilo_visual__in=['sin_preferencia', 'moderno', 'minimalista', 'elegante', 'colorido', 'corporativo']),
                name='requerimiento_estilo_valido',
            ),
            models.CheckConstraint(check=models.Q(situacion_logo__in=['tiene', 'mejorar', 'crear']), name='requerimiento_logo_valido'),
            models.CheckConstraint(
                check=models.Q(presupuesto__in=['por_definir', 'menos_300', '300_600', '600_1000', 'mas_1000']),
                name='requerimiento_presupuesto_valido',
            ),
            models.CheckConstraint(check=models.Q(medio_contacto__in=['correo', 'telefono', 'whatsapp']), name='requerimiento_contacto_valido'),
        ]

    def __str__(self):
        return f'{self.nombre_negocio} ({self.get_tipo_sitio_display()})'

    # Nombre legible del rubro (por ejemplo "Gastronomía").
    @property
    def nombre_rubro(self):
        from .estimacion import RUBROS
        return dict(RUBROS).get(self.rubro, self.rubro)

    # Nombres legibles de las secciones elegidas en el paso 4.
    @property
    def nombres_secciones(self):
        etiquetas = dict(self.SECCIONES)
        return [etiquetas[clave] for clave in self.secciones if clave in etiquetas]

    # Sitios de referencia como lista, uno por línea.
    @property
    def lista_referencias(self):
        return [linea.strip() for linea in self.sitios_referencia.splitlines() if linea.strip()]


# Tabla plataforma_solicitud (Tabla 18): clase central. Hay una por cada pedido de un cliente (CU08).
class Solicitud(models.Model):
    TIPOS = Servicio.TIPOS
    PRIORIDADES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]

    numero = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False)
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='solicitudes')
    tipo = models.CharField(max_length=20, choices=TIPOS)
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    url_sitio = models.URLField('sitio web', blank=True)
    detalles = models.JSONField(default=dict, blank=True)
    requerimiento = models.OneToOneField(RequerimientoWeb, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitud')
    estado = models.ForeignKey(EstadoSolicitud, on_delete=models.PROTECT, related_name='solicitudes')
    prioridad = models.CharField(max_length=10, choices=PRIORIDADES, default='media')
    fecha_deseada = models.DateField('fecha deseada de entrega', null=True, blank=True)
    notas_internas = models.TextField(blank=True)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes_asignadas',
        limit_choices_to={'is_staff': True},
    )
    relacionada = models.ForeignKey(
        'self',
        verbose_name='solicitud relacionada',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='derivadas',
    )
    token_envio = models.UUIDField(null=True, blank=True, unique=True, editable=False)
    fecha_primera_respuesta = models.DateTimeField(null=True, blank=True, editable=False)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_solicitud']
        verbose_name = 'solicitud'
        verbose_name_plural = 'solicitudes'
        indexes = [
            models.Index(fields=['estado', '-fecha_solicitud'], name='solicitud_estado_fecha'),
            models.Index(fields=['estado', '-fecha_actualizacion'], name='solicitud_estado_actualizada'),
            models.Index(fields=['cliente', '-fecha_solicitud'], name='solicitud_cliente_fecha'),
            models.Index(fields=['responsable', 'estado'], name='solicitud_responsable'),
            models.Index(fields=['tipo', '-fecha_solicitud'], name='solicitud_tipo_fecha'),
            models.Index(fields=['prioridad', 'fecha_solicitud'], name='solicitud_prioridad'),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(prioridad__in=['baja', 'media', 'alta', 'urgente']), name='solicitud_prioridad_valida'),
            models.CheckConstraint(check=models.Q(tipo__in=['Creacion', 'Mejora', 'Soporte', 'Mantenimiento']), name='solicitud_tipo_valido'),
        ]

    def __str__(self):
        return f'{self.numero} - {self.titulo}'

    # Al guardarla por primera vez le asigna el número correlativo AXZ-AAMM-NNNN.
    def save(self, *args, **kwargs):
        if self.estado_id is None:
            self.estado = EstadoSolicitud.obtener(EstadoSolicitud.RECIBIDA)
        if self.pk or self.numero:
            super().save(*args, **kwargs)
            return
        with transaction.atomic():
            super().save(*args, **kwargs)
            fecha = timezone.localtime(self.fecha_solicitud).strftime('%y%m')
            self.numero = f'AXZ-{fecha}-{self.pk:04d}'
            super().save(update_fields=['numero'])

    # Página de detalle que ve el cliente (CU11).
    def get_absolute_url(self):
        return reverse('ver_solicitud', args=[self.pk])

    # El cliente solo puede cancelar mientras no se haya emitido una cotización.
    @property
    def cancelable(self):
        return self.estado.codigo in (EstadoSolicitud.RECIBIDA, EstadoSolicitud.EN_REVISION)

    # Indica si hay una cotización vigente esperando la respuesta del cliente (CU12).
    @property
    def cotizacion_pendiente(self):
        return self.estado.codigo == EstadoSolicitud.COTIZADA and hasattr(self, 'cotizacion')

    # Plazo de primera respuesta, en horas, según la prioridad.
    @property
    def horas_sla(self):
        return settings.AXZTRA['SLA_HORAS'].get(self.prioridad, 48)

    # Fecha límite para la primera respuesta del equipo.
    @property
    def vence_respuesta(self):
        return self.fecha_solicitud + timedelta(hours=self.horas_sla)

    # Verdadero si sigue en Recibida y ya pasó el plazo de respuesta.
    @property
    def atrasada(self):
        return self.estado.codigo == EstadoSolicitud.RECIBIDA and timezone.now() > self.vence_respuesta

    # Etapas que se muestran en la barra de avance del cliente (CU11).
    @property
    def pasos_seguimiento(self):
        estados = EstadoSolicitud.todos()
        actual = self.estado.codigo
        flujo = EstadoSolicitud.FLUJO
        indice_actual = flujo.index(actual) if actual in flujo else -1
        pasos = []
        for indice, codigo in enumerate(flujo):
            if indice_actual == -1 or indice > indice_actual:
                situacion = 'pendiente'
            elif indice < indice_actual:
                situacion = 'hecho'
            else:
                situacion = 'actual'
            estado = estados.get(codigo)
            pasos.append({'nombre': estado.nombre if estado else codigo, 'situacion': situacion})
        return pasos

    # Filtro para consultar todas las solicitudes atrasadas en una sola consulta.
    @classmethod
    def filtro_atrasadas(cls):
        ahora = timezone.now()
        condicion = models.Q()
        for prioridad, horas in settings.AXZTRA['SLA_HORAS'].items():
            condicion |= models.Q(prioridad=prioridad, fecha_solicitud__lt=ahora - timedelta(hours=horas))
        return models.Q(estado__codigo=EstadoSolicitud.RECIBIDA) & condicion


# Tabla plataforma_estimacion (Tabla 20): estimación referencial calculada con la fórmula de la sección 3.5.
class Estimacion(models.Model):
    solicitud = models.OneToOneField(Solicitud, on_delete=models.CASCADE, related_name='estimacion')
    total = models.PositiveIntegerField()
    monto_minimo = models.PositiveIntegerField()
    monto_maximo = models.PositiveIntegerField()
    factor_complejidad = models.DecimalField(max_digits=4, decimal_places=2, default=1)
    desglose = models.JSONField(default=list, blank=True)
    semanas_minimas = models.PositiveSmallIntegerField(default=1)
    semanas_maximas = models.PositiveSmallIntegerField(default=2)
    es_referencial = models.BooleanField(default=True)
    fecha_calculo = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'estimación'
        verbose_name_plural = 'estimaciones'
        constraints = [
            models.CheckConstraint(check=models.Q(monto_minimo__lte=models.F('monto_maximo')), name='estimacion_rango_valido'),
            models.CheckConstraint(check=models.Q(semanas_minimas__lte=models.F('semanas_maximas')), name='estimacion_plazo_valido'),
        ]

    def __str__(self):
        return f'Estimación {self.solicitud.numero}'


# Tabla plataforma_cotizacion (Tabla 21): cotización definitiva que emite el equipo (CU16).
class Cotizacion(models.Model):
    solicitud = models.OneToOneField(Solicitud, on_delete=models.CASCADE, related_name='cotizacion')
    monto = models.PositiveIntegerField('monto neto (CLP)')
    items = models.JSONField(default=list, blank=True)
    plazo_dias = models.PositiveSmallIntegerField('plazo de entrega (días hábiles)')
    validez_dias = models.PositiveSmallIntegerField('validez (días)', default=15)
    detalle = models.TextField('alcance y condiciones')
    version = models.PositiveSmallIntegerField(default=1)
    emitida_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='cotizaciones_emitidas')
    fecha_emision = models.DateTimeField(default=timezone.now)
    respuesta_cliente = models.CharField(max_length=10, blank=True, choices=[('aceptada', 'Aceptada'), ('rechazada', 'Rechazada')])
    comentario_cliente = models.TextField(blank=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'cotización'
        verbose_name_plural = 'cotizaciones'
        constraints = [
            models.CheckConstraint(check=models.Q(plazo_dias__gte=1), name='cotizacion_plazo_positivo'),
            models.CheckConstraint(check=models.Q(validez_dias__gte=1), name='cotizacion_validez_positiva'),
            models.CheckConstraint(check=models.Q(version__gte=1), name='cotizacion_version_positiva'),
            models.CheckConstraint(check=models.Q(respuesta_cliente__in=['', 'aceptada', 'rechazada']), name='cotizacion_respuesta_valida'),
        ]

    def __str__(self):
        return f'Cotización {self.solicitud.numero}'

    # Fecha en que vence la cotización (emisión + días de validez).
    @property
    def fecha_vencimiento(self):
        return self.fecha_emision + timedelta(days=self.validez_dias)

    # Verdadero mientras no haya vencido.
    @property
    def vigente(self):
        return timezone.now() <= self.fecha_vencimiento

    # IVA del 19% calculado sobre el monto neto.
    @property
    def monto_iva(self):
        return round(self.monto * settings.AXZTRA['IVA'] / 100)

    # Total con IVA.
    @property
    def total(self):
        return self.monto + self.monto_iva

    # Ítems de la cotización con su subtotal calculado.
    @property
    def lineas(self):
        if self.items:
            return self.items
        return [{'descripcion': self.solicitud.titulo, 'cantidad': 1, 'precio_unitario': self.monto, 'subtotal': self.monto}]


# Tabla plataforma_historialsolicitud (Tabla 22): queda un registro por cada cambio de estado.
class HistorialSolicitud(models.Model):
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, related_name='historial')
    estado_anterior = models.ForeignKey(EstadoSolicitud, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    estado_nuevo = models.ForeignKey(EstadoSolicitud, on_delete=models.PROTECT, related_name='+')
    comentario = models.TextField(blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-pk']
        verbose_name = 'historial de solicitud'
        verbose_name_plural = 'historial de solicitudes'
        indexes = [
            models.Index(fields=['solicitud', '-fecha'], name='historial_solicitud_fecha'),
        ]

    def __str__(self):
        return f'{self.solicitud.numero}: {self.estado_nuevo}'


# Tabla plataforma_mensajesolicitud (Tabla 23): conversación entre el cliente y el equipo (CU13).
class MensajeSolicitud(models.Model):
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, related_name='mensajes')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='mensajes_solicitud')
    es_equipo = models.BooleanField(default=False)
    texto = models.TextField()
    leido = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha', 'pk']
        verbose_name = 'mensaje de solicitud'
        verbose_name_plural = 'mensajes de solicitudes'
        indexes = [
            models.Index(fields=['solicitud', 'es_equipo', 'leido'], name='mensaje_no_leidos'),
            models.Index(fields=['es_equipo', 'leido'], name='mensaje_pendientes'),
        ]
        constraints = [
            models.CheckConstraint(check=~models.Q(texto=''), name='mensaje_con_texto'),
        ]

    def __str__(self):
        return f'{self.solicitud.numero}: {self.texto[:40]}'


# Carpeta donde se guarda cada archivo: adjuntos/<número de solicitud>/<nombre aleatorio>.
def ruta_adjunto(instancia, nombre):
    extension = os.path.splitext(nombre)[1].lower()[:10]
    fecha = timezone.now().strftime('%Y/%m')
    return f'adjuntos/{fecha}/{uuid.uuid4().hex}{extension}'


# Tabla plataforma_adjunto (Tabla 24): archivos asociados a una solicitud (CU10).
class Adjunto(models.Model):
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, related_name='adjuntos')
    archivo = models.FileField(upload_to=ruta_adjunto, max_length=255)
    nombre_original = models.CharField(max_length=255)
    tamano = models.PositiveIntegerField(default=0)
    tipo_contenido = models.CharField(max_length=120, blank=True)
    subido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='adjuntos_subidos')
    es_equipo = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-pk']
        verbose_name = 'archivo adjunto'
        verbose_name_plural = 'archivos adjuntos'

    def __str__(self):
        return self.nombre_original

    # Extensión del archivo en minúsculas (pdf, jpg, etc.).
    @property
    def extension(self):
        return os.path.splitext(self.nombre_original)[1].lower().lstrip('.')

    # Ícono que se muestra según el tipo de archivo.
    @property
    def icono(self):
        iconos = {
            'pdf': 'fa-regular fa-file-pdf',
            'png': 'fa-regular fa-file-image', 'jpg': 'fa-regular fa-file-image', 'jpeg': 'fa-regular fa-file-image',
            'webp': 'fa-regular fa-file-image', 'gif': 'fa-regular fa-file-image',
            'docx': 'fa-regular fa-file-word', 'xlsx': 'fa-regular fa-file-excel', 'pptx': 'fa-regular fa-file-powerpoint',
            'zip': 'fa-regular fa-file-zipper', 'txt': 'fa-regular fa-file-lines',
        }
        return iconos.get(self.extension, 'fa-regular fa-file')


# Tabla plataforma_preguntafrecuente (Tabla 29): preguntas de la portada; el asistente también las usa.
class PreguntaFrecuente(models.Model):
    pregunta = models.CharField(max_length=200)
    respuesta = models.TextField()
    palabras_clave = models.CharField(
        max_length=300,
        blank=True,
        help_text='Palabras separadas por coma que ayudan al asistente a encontrar esta respuesta.',
    )
    orden = models.PositiveIntegerField(default=0)
    activa = models.BooleanField(default=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['orden', 'pk']
        verbose_name = 'pregunta frecuente'
        verbose_name_plural = 'preguntas frecuentes'
        constraints = [
            models.UniqueConstraint(Lower('pregunta'), name='pregunta_frecuente_unica'),
        ]

    def __str__(self):
        return self.pregunta


# Tabla plataforma_configuracionsitio (Tabla 30): datos de contacto y aviso del sitio. Siempre existe un solo registro.
class ConfiguracionSitio(models.Model):
    correo_contacto = models.EmailField('correo de contacto', default='contacto@axztra.cl')
    whatsapp = models.CharField('número de WhatsApp', max_length=20, default='56912345678', help_text='Solo dígitos, con código de país. Ejemplo: 56912345678')
    whatsapp_visible = models.CharField('WhatsApp como se muestra', max_length=30, default='+56 9 1234 5678')
    ubicacion = models.CharField('ubicación', max_length=150, default='Hualpén, Región del Biobío, Chile')
    horario = models.CharField('horario de atención', max_length=150, default='Lunes a viernes, de 9:00 a 18:00 horas')
    aviso = models.CharField('aviso destacado', max_length=200, blank=True, help_text='Mensaje breve que se muestra sobre el menú del sitio. Déjalo vacío para ocultarlo.')
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'configuración del sitio'
        verbose_name_plural = 'configuración del sitio'
        constraints = [
            models.CheckConstraint(check=models.Q(pk=1), name='configuracion_registro_unico'),
        ]

    def __str__(self):
        return 'Configuración del sitio'

    # Fuerza el id 1 para que nunca haya más de un registro.
    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(CLAVE_CACHE_CONFIGURACION)

    # Devuelve la configuración vigente (desde la caché si está disponible).
    @classmethod
    def actual(cls):
        configuracion = cache.get(CLAVE_CACHE_CONFIGURACION)
        if configuracion is None:
            configuracion, _ = cls.objects.get_or_create(pk=1)
            cache.set(CLAVE_CACHE_CONFIGURACION, configuracion, 600)
        return configuracion


# Tabla plataforma_registroactividad (Tabla 28): auditoría de las acciones del equipo (CU20).
class RegistroActividad(models.Model):
    ACCIONES = [
        ('acceso', 'Acceso al panel'),
        ('estado', 'Cambio de estado'),
        ('cotizacion', 'Cotización emitida'),
        ('asignacion', 'Asignación de responsable'),
        ('gestion', 'Gestión interna'),
        ('mensaje', 'Mensaje al cliente'),
        ('adjunto', 'Archivo adjunto'),
        ('servicio', 'Catálogo de servicios'),
        ('contenido', 'Contenido del sitio'),
        ('exportacion', 'Exportación de datos'),
        ('cuenta', 'Cuenta de usuario'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='actividad')
    accion = models.CharField(max_length=20, choices=ACCIONES)
    descripcion = models.CharField(max_length=300)
    solicitud = models.ForeignKey(Solicitud, on_delete=models.SET_NULL, null=True, blank=True, related_name='actividad')
    ip = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-fecha', '-pk']
        verbose_name = 'registro de actividad'
        verbose_name_plural = 'registro de actividad'
        indexes = [
            models.Index(fields=['accion', '-fecha'], name='actividad_accion_fecha'),
        ]

    def __str__(self):
        return f'{self.get_accion_display()}: {self.descripcion}'


# Tabla plataforma_tokenapi (Tabla 27): tokens para que sistemas externos usen la API (CU22).
class TokenAPI(models.Model):
    nombre = models.CharField(max_length=100)
    prefijo = models.CharField(max_length=8, db_index=True, editable=False)
    token_hash = models.CharField(max_length=64, editable=False)
    activo = models.BooleanField(default=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    ultimo_uso = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'token de integración'
        verbose_name_plural = 'tokens de integración'

    def __str__(self):
        return f'{self.nombre} ({self.prefijo}...)'

    # Solo se guarda la huella SHA-256 del token, nunca el token completo.
    @staticmethod
    def calcular_hash(valor):
        return hashlib.sha256(valor.encode('utf-8')).hexdigest()

    # Crea un token nuevo y devuelve el texto completo una única vez.
    @classmethod
    def generar(cls, nombre, usuario=None):
        valor = f'axz_{secrets.token_urlsafe(32)}'
        token = cls.objects.create(
            nombre=nombre,
            prefijo=valor[:8],
            token_hash=cls.calcular_hash(valor),
            creado_por=usuario,
        )
        return token, valor


# Tabla plataforma_mensajeasistente (Tabla 25): mensajes de las conversaciones con el asistente virtual (CU03).
class MensajeAsistente(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='mensajes_asistente')
    sesion = models.CharField(max_length=64, db_index=True)
    contenido = models.TextField()
    es_asistente = models.BooleanField(default=False)
    intencion = models.CharField(max_length=40, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha', 'pk']
        verbose_name = 'mensaje del asistente'
        verbose_name_plural = 'mensajes del asistente'
        indexes = [
            models.Index(fields=['usuario', 'fecha'], name='asistente_usuario_fecha'),
            models.Index(fields=['es_asistente', 'fecha'], name='asistente_tipo_fecha'),
        ]

    def __str__(self):
        autor = 'Asistente' if self.es_asistente else 'Usuario'
        return f'{autor}: {self.contenido[:50]}'


# Tabla plataforma_codigoverificacion (Tabla 26): códigos de 6 dígitos de la verificación en dos pasos (CU07).
class CodigoVerificacion(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='codigos_verificacion')
    codigo_hash = models.CharField(max_length=128)
    creado = models.DateTimeField(auto_now_add=True)
    expira = models.DateTimeField()
    intentos = models.PositiveSmallIntegerField(default=0)
    usado = models.BooleanField(default=False)

    class Meta:
        ordering = ['-creado']
        verbose_name = 'código de verificación'
        verbose_name_plural = 'códigos de verificación'
        indexes = [
            models.Index(fields=['usuario', 'usado'], name='codigo_usuario_usado'),
        ]

    def __str__(self):
        return f'Código de {self.usuario} ({self.creado:%d-%m-%Y %H:%M})'
