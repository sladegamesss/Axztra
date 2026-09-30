from datetime import timedelta

from django.conf import settings
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


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

    def __str__(self):
        return self.nombre

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

    def get_absolute_url(self):
        return reverse('servicio_detalle', args=[self.slug])

    @property
    def lista_incluye(self):
        return [linea.strip() for linea in self.incluye.splitlines() if linea.strip()]

    @property
    def icono(self):
        return self.categoria.icono if self.categoria else 'fa-solid fa-code'

    @property
    def url_solicitud(self):
        rutas = {
            self.TIPO_CREACION: 'crear_web',
            self.TIPO_MEJORA: 'solicitar_mejora',
            self.TIPO_SOPORTE: 'solicitar_soporte',
            self.TIPO_MANTENIMIENTO: 'solicitar_mantenimiento',
        }
        return f"{reverse(rutas[self.tipo])}?servicio={self.pk}"


class PerfilCliente(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil_cliente')
    empresa = models.CharField('empresa o emprendimiento', max_length=200, blank=True)
    telefono = models.CharField('teléfono', max_length=20, blank=True)
    rut = models.CharField('RUT', max_length=12, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    recibir_notificaciones = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'perfil de cliente'
        verbose_name_plural = 'perfiles de cliente'

    def __str__(self):
        return self.usuario.get_full_name() or self.usuario.email


class EstadoSolicitud(models.Model):
    RECIBIDA = 'recibida'
    EN_REVISION = 'en_revision'
    COTIZADA = 'cotizada'
    APROBADA = 'aprobada'
    EN_DESARROLLO = 'en_desarrollo'
    COMPLETADA = 'completada'
    RECHAZADA = 'rechazada'
    CANCELADA = 'cancelada'

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

    @classmethod
    def obtener(cls, codigo):
        return cls.objects.get(codigo=codigo)


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

    nombre_negocio = models.CharField(max_length=150)
    rubro = models.CharField(max_length=60)
    descripcion_negocio = models.TextField()
    publico_objetivo = models.CharField(max_length=200, blank=True)
    tipo_sitio = models.CharField(max_length=20, choices=TIPOS_SITIO)
    tiene_sitio_actual = models.BooleanField(default=False)
    url_sitio_actual = models.URLField(blank=True)
    objetivos = models.JSONField(default=list, blank=True)
    num_paginas = models.PositiveSmallIntegerField(default=5)
    complejidad = models.CharField(max_length=10, choices=COMPLEJIDADES, default='media')
    funcionalidades = models.JSONField(default=list, blank=True)
    integraciones = models.JSONField(default=list, blank=True)
    tiene_contenido = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'requerimiento web'
        verbose_name_plural = 'requerimientos web'

    def __str__(self):
        return f'{self.nombre_negocio} ({self.get_tipo_sitio_display()})'

    @property
    def nombre_rubro(self):
        from .estimacion import RUBROS
        return dict(RUBROS).get(self.rubro, self.rubro)


class Solicitud(models.Model):
    TIPOS = Servicio.TIPOS
    PRIORIDADES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]

    numero = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False)
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='solicitudes')
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
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_solicitud']
        verbose_name = 'solicitud'
        verbose_name_plural = 'solicitudes'

    def __str__(self):
        return f'{self.numero} · {self.titulo}'

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

    def get_absolute_url(self):
        return reverse('ver_solicitud', args=[self.pk])

    @property
    def cancelable(self):
        return self.estado.codigo in (EstadoSolicitud.RECIBIDA, EstadoSolicitud.EN_REVISION)

    @property
    def cotizacion_pendiente(self):
        return self.estado.codigo == EstadoSolicitud.COTIZADA and hasattr(self, 'cotizacion')

    @property
    def pasos_seguimiento(self):
        flujo = [
            EstadoSolicitud.RECIBIDA,
            EstadoSolicitud.EN_REVISION,
            EstadoSolicitud.COTIZADA,
            EstadoSolicitud.APROBADA,
            EstadoSolicitud.EN_DESARROLLO,
            EstadoSolicitud.COMPLETADA,
        ]
        nombres = dict(EstadoSolicitud.objects.filter(codigo__in=flujo).values_list('codigo', 'nombre'))
        actual = self.estado.codigo
        indice_actual = flujo.index(actual) if actual in flujo else -1
        pasos = []
        for indice, codigo in enumerate(flujo):
            if indice_actual == -1:
                situacion = 'pendiente'
            elif indice < indice_actual:
                situacion = 'hecho'
            elif indice == indice_actual:
                situacion = 'actual'
            else:
                situacion = 'pendiente'
            pasos.append({'nombre': nombres.get(codigo, codigo), 'situacion': situacion})
        return pasos


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

    def __str__(self):
        return f'Estimación {self.solicitud.numero}'


class Cotizacion(models.Model):
    solicitud = models.OneToOneField(Solicitud, on_delete=models.CASCADE, related_name='cotizacion')
    monto = models.PositiveIntegerField('monto final (CLP)')
    plazo_dias = models.PositiveSmallIntegerField('plazo de entrega (días hábiles)')
    validez_dias = models.PositiveSmallIntegerField('validez (días)', default=15)
    detalle = models.TextField('alcance y condiciones')
    emitida_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='cotizaciones_emitidas')
    fecha_emision = models.DateTimeField(default=timezone.now)
    respuesta_cliente = models.CharField(max_length=10, blank=True, choices=[('aceptada', 'Aceptada'), ('rechazada', 'Rechazada')])
    comentario_cliente = models.TextField(blank=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'cotización'
        verbose_name_plural = 'cotizaciones'

    def __str__(self):
        return f'Cotización {self.solicitud.numero}'

    @property
    def fecha_vencimiento(self):
        return self.fecha_emision + timedelta(days=self.validez_dias)

    @property
    def vigente(self):
        return timezone.now() <= self.fecha_vencimiento


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

    def __str__(self):
        return f'{self.solicitud.numero}: {self.estado_nuevo}'


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

    def __str__(self):
        autor = 'Asistente' if self.es_asistente else 'Usuario'
        return f'{autor}: {self.contenido[:50]}'


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

    def __str__(self):
        return f'Código de {self.usuario} ({self.creado:%d-%m-%Y %H:%M})'
    
class PlataformaFormulario(models.Model):
    """
    Representa la tabla FORMULARIO de tu MER
    """
    solicitud_id = models.IntegerField()
    tipo_servicio = models.CharField(max_length=100)
    datos = models.JSONField(default=dict)
    completado = models.BooleanField(default=False)
    fecha_envio = models.DateTimeField(blank=True, null=True)

    class Meta:
        # Corregido: db_table junto y con guion bajo
        db_table = 'plataforma_formulario'

    def __str__(self):
        # Corregido: Ahora apunta correctamente al campo solicitud_id
        return f"Formulario {self.id} - Solicitud {self.solicitud_id}"

    
