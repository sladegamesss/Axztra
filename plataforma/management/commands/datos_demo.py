"""
Comando: python manage.py datos_demo [--reiniciar]

Crea las cuentas, solicitudes, cotizaciones, mensajes y consultas de demostración.
Se puede ejecutar varias veces sin duplicar información.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand
from django.db import transaction
from django.test.utils import override_settings
from django.utils import timezone

from plataforma import gestion
from plataforma.asistente import AsistenteVirtual
from plataforma.models import (
    Cotizacion,
    EstadoSolicitud,
    Estimacion,
    HistorialSolicitud,
    MensajeAsistente,
    MensajeSolicitud,
    PerfilCliente,
    RegistroActividad,
    Servicio,
    Solicitud,
)

User = get_user_model()

ADMIN = {'email': 'admin@axztra.cl', 'password': 'AxztraAdmin2026', 'first_name': 'Camilo', 'last_name': 'Barra'}
EQUIPO = [
    {
        'email': 'desarrollo@axztra.cl', 'password': 'Equipo2026', 'first_name': 'Benjamín', 'last_name': 'Ruiz',
        'permisos': ['change_servicio', 'add_servicio', 'change_categoria', 'add_categoria', 'change_preguntafrecuente', 'add_preguntafrecuente'],
    },
    {'email': 'soporte@axztra.cl', 'password': 'Equipo2026', 'first_name': 'Franco', 'last_name': 'Constanzo', 'permisos': []},
]
CLIENTES = [
    {'email': 'cliente@axztra.cl', 'first_name': 'María', 'last_name': 'González', 'empresa': 'Cafetería Aroma', 'ciudad': 'Concepción', 'telefono': '+56 9 5123 4567'},
    {'email': 'carlos.perez@axztra.cl', 'first_name': 'Carlos', 'last_name': 'Pérez', 'empresa': 'Ferretería El Faro', 'ciudad': 'Talcahuano', 'telefono': '+56 9 6234 5678'},
    {'email': 'fundacion.vida@axztra.cl', 'first_name': 'Paula', 'last_name': 'Muñoz', 'empresa': 'Fundación Vida', 'ciudad': 'Hualpén', 'telefono': '+56 9 7345 6789'},
    {'email': 'andrea.rojas@axztra.cl', 'first_name': 'Andrea', 'last_name': 'Rojas', 'empresa': 'Clínica Dental Sonríe', 'ciudad': 'Chiguayante', 'telefono': '+56 9 8456 7890'},
    {'email': 'jorge.soto@axztra.cl', 'first_name': 'Jorge', 'last_name': 'Soto', 'empresa': 'Constructora Soto', 'ciudad': 'San Pedro de la Paz', 'telefono': '+56 9 9567 8901'},
]
CLAVE_CLIENTES = 'Cliente2026'

CONSULTAS = [
    '¿Cuánto cuesta una página web?',
    'Tengo una pastelería, ¿qué le pondrías a mi sitio?',
    '¿Cuánto se demoran en entregar?',
    'Mi sitio está caído, necesito ayuda',
    '¿Aceptan pago con tarjeta?',
    '¿Qué incluye el mantenimiento?',
    'Quiero una tienda online',
    '¿Hacen aplicaciones para celular?',
]


class Command(BaseCommand):
    help = 'Crea usuarios, solicitudes y consultas de demostración para presentar la plataforma.'

    def add_arguments(self, parser):
        parser.add_argument('--reiniciar', action='store_true', help='Elimina los datos de demostración existentes y los crea nuevamente.')

    # Crea o actualiza una cuenta de demostración.
    def _usuario(self, datos, clave, staff=False, superusuario=False):
        usuario, creado = User.objects.get_or_create(
            username=datos['email'],
            defaults={
                'email': datos['email'],
                'first_name': datos['first_name'],
                'last_name': datos['last_name'],
                'is_staff': staff,
                'is_superuser': superusuario,
            },
        )
        if creado:
            usuario.set_password(clave)
            usuario.save()
        return usuario, creado

    # Punto de entrada del comando.
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.dummy.EmailBackend')
    def handle(self, *args, **opciones):
        with transaction.atomic():
            admin, admin_creado = self._usuario(ADMIN, ADMIN['password'], staff=True, superusuario=True)
            equipo = []
            for datos in EQUIPO:
                persona, _ = self._usuario(datos, datos['password'], staff=True)
                if datos['permisos']:
                    persona.user_permissions.add(*Permission.objects.filter(content_type__app_label='plataforma', codename__in=datos['permisos']))
                equipo.append(persona)
            clientes = []
            for datos in CLIENTES:
                cliente, creado = self._usuario(datos, CLAVE_CLIENTES)
                PerfilCliente.objects.update_or_create(
                    usuario=cliente,
                    defaults={
                        'empresa': datos['empresa'],
                        'ciudad': datos['ciudad'],
                        'telefono': datos['telefono'],
                        'fecha_aceptacion_terminos': timezone.now(),
                    },
                )
                clientes.append(cliente)

            if opciones['reiniciar']:
                Solicitud.objects.filter(cliente__in=clientes).delete()
                MensajeAsistente.objects.filter(usuario__in=clientes).delete()
                MensajeAsistente.objects.filter(usuario__isnull=True, sesion__startswith='demo-').delete()

            if Solicitud.objects.filter(cliente__in=clientes).exists():
                self.stdout.write(self.style.WARNING('Los clientes de demostración ya tienen solicitudes. Usa --reiniciar para regenerarlas.'))
            else:
                self._crear_solicitudes(admin, equipo, clientes)
                self._crear_consultas(clientes)

        self.stdout.write(self.style.SUCCESS('Datos de demostración listos.'))
        self.stdout.write(f"  Administrador: {ADMIN['email']} / {ADMIN['password']}" + ('' if admin_creado else ' (ya existía, se mantuvo su contraseña)'))
        self.stdout.write(f"  Equipo:        {EQUIPO[1]['email']} / {EQUIPO[1]['password']}")
        self.stdout.write(f"  Cliente:       {CLIENTES[0]['email']} / {CLAVE_CLIENTES}")

    # Ajusta las fechas para que el historial se vea realista.
    def _fechar(self, solicitud, inicio, horas, primera_respuesta=True):
        historial = list(HistorialSolicitud.objects.filter(solicitud=solicitud).order_by('pk'))
        fechas = [inicio] + [inicio + timedelta(hours=h) for h in horas]
        fechas += [fechas[-1]] * max(0, len(historial) - len(fechas))
        for registro, fecha in zip(historial, fechas):
            HistorialSolicitud.objects.filter(pk=registro.pk).update(fecha=fecha)
        ultima = fechas[len(historial) - 1] if historial else inicio
        Solicitud.objects.filter(pk=solicitud.pk).update(
            numero=f'AXZ-{timezone.localtime(inicio):%y%m}-{solicitud.pk:04d}',
            fecha_solicitud=inicio,
            fecha_actualizacion=ultima,
            fecha_primera_respuesta=fechas[1] if primera_respuesta and len(historial) > 1 else None,
        )
        Estimacion.objects.filter(solicitud=solicitud).update(fecha_calculo=inicio)
        cotizada = [r for r, f in zip(historial, fechas) if r.estado_nuevo.codigo == EstadoSolicitud.COTIZADA]
        if cotizada:
            indice = historial.index(cotizada[-1])
            Cotizacion.objects.filter(solicitud=solicitud).update(fecha_emision=fechas[indice])
            respuesta = [f for r, f in zip(historial, fechas) if r.estado_nuevo.codigo in (EstadoSolicitud.APROBADA, EstadoSolicitud.RECHAZADA)]
            if respuesta:
                Cotizacion.objects.filter(solicitud=solicitud).update(fecha_respuesta=respuesta[0])
        RegistroActividad.objects.filter(solicitud=solicitud).update(fecha=ultima)

    # Agrega un mensaje de ejemplo a una solicitud.
    def _mensaje(self, solicitud, autor, texto, fecha, leido=True):
        mensaje = gestion.enviar_mensaje(solicitud, autor, texto)
        MensajeSolicitud.objects.filter(pk=mensaje.pk).update(fecha=fecha, leido=leido)
        Solicitud.objects.filter(pk=solicitud.pk, fecha_actualizacion__gt=fecha).update(fecha_actualizacion=fecha)
        RegistroActividad.objects.filter(solicitud=solicitud, accion='mensaje', fecha__gt=fecha).update(fecha=fecha)
        return mensaje

    # Emite una cotización de ejemplo con sus ítems.
    def _cotizar(self, solicitud, admin, items, plazo, validez, detalle):
        cotizacion = Cotizacion(plazo_dias=plazo, validez_dias=validez, detalle=detalle)
        lineas = [
            {'descripcion': descripcion, 'cantidad': cantidad, 'precio_unitario': precio, 'subtotal': cantidad * precio}
            for descripcion, cantidad, precio in items
        ]
        return gestion.emitir_cotizacion(solicitud, cotizacion, lineas, admin)

    # Solicitudes de ejemplo en distintos estados del flujo.
    def _crear_solicitudes(self, admin, equipo, clientes):
        benjamin, franco = equipo
        maria, carlos, paula, andrea, jorge = clientes
        estado = EstadoSolicitud.obtener
        ahora = timezone.now()
        servicio = lambda slug: Servicio.objects.filter(slug=slug).first()

        cancelada = gestion.crear_solicitud(carlos, Servicio.TIPO_MANTENIMIENTO, {
            'servicio': servicio('mantenimiento-mensual'),
            'titulo': 'Mantenimiento del sitio informativo',
            'descripcion': 'Queremos respaldos mensuales del sitio actual.',
            'url_sitio': 'https://ferreteriaelfaro.cl',
        }, detalles={'Plataforma': 'WordPress', 'Frecuencia': 'Mensual', 'Tareas': ['Respaldos periódicos']})
        gestion.cancelar_solicitud(cancelada, carlos)
        self._fechar(cancelada, ahora - timedelta(days=150), [20], primera_respuesta=False)

        mejora = gestion.crear_solicitud(maria, Servicio.TIPO_MEJORA, {
            'servicio': servicio('optimizacion-velocidad-seo'),
            'titulo': 'Mejorar velocidad del blog de la cafetería',
            'descripcion': 'El blog tarda mucho en cargar desde el celular y casi no aparece en Google.',
            'url_sitio': 'https://blog.cafeteriaaroma.cl',
        }, detalles={'Mejoras solicitadas': ['Mejorar velocidad de carga', 'Posicionamiento en buscadores (SEO)']})
        gestion.asignar_responsable(mejora, franco, admin)
        gestion.cambiar_estado(mejora, estado(EstadoSolicitud.EN_REVISION), franco, 'Revisamos el sitio: las imágenes pesan demasiado y faltan metadatos.', notificar=False)
        gestion.cambiar_estado(mejora, estado(EstadoSolicitud.EN_DESARROLLO), franco, 'Iniciamos la optimización.', notificar=False)
        gestion.cambiar_estado(mejora, estado(EstadoSolicitud.COMPLETADA), franco, 'Optimización terminada. El sitio ahora carga en menos de 2 segundos.', notificar=False)
        self._fechar(mejora, ahora - timedelta(days=128), [6, 30, 200])

        corporativo = gestion.crear_solicitud_web(jorge, {
            'servicio': servicio('sitio-web-corporativo'),
            'titulo': 'Sitio corporativo Constructora Soto',
            'tipo_sitio': 'corporativo',
            'tiene_sitio_actual': 'no',
            'nombre_negocio': 'Constructora Soto',
            'rubro': 'construccion',
            'descripcion_negocio': 'Constructora de viviendas y ampliaciones con 15 años en la zona. Queremos mostrar proyectos terminados y recibir solicitudes de presupuesto.',
            'publico_objetivo': 'Familias que quieren construir o ampliar su casa',
            'objetivos': ['presencia', 'clientes', 'mostrar'],
            'funcionalidades': ['formulario', 'galeria', 'blog'],
            'integraciones': ['whatsapp', 'mapa'],
            'num_paginas': 8,
            'complejidad': 'media',
            'tiene_contenido': True,
            'estilo_visual': 'corporativo',
            'colores': 'Gris grafito y amarillo',
            'secciones': ['inicio', 'nosotros', 'servicios', 'galeria', 'contacto'],
            'situacion_logo': 'tiene',
            'dominio': 'constructorasoto.cl',
            'presupuesto': '600_1000',
            'medio_contacto': 'telefono',
        })
        gestion.asignar_responsable(corporativo, benjamin, admin)
        gestion.cambiar_estado(corporativo, estado(EstadoSolicitud.EN_REVISION), benjamin, notificar=False)
        self._cotizar(corporativo, admin, [
            ('Sitio corporativo de 8 páginas: diseño y desarrollo', 1, 520000),
            ('Galería de proyectos y blog', 1, 190000),
            ('Formulario de presupuesto, WhatsApp y mapa', 1, 90000),
        ], 25, 15, 'Incluye diseño a medida, adaptación a celulares, publicación y una capacitación de 1 hora.')
        gestion.responder_cotizacion(corporativo, 'rechazada', 'El presupuesto supera lo que tenemos disponible este año.', jorge)
        self._fechar(corporativo, ahora - timedelta(days=96), [4, 26, 70])

        tienda = gestion.crear_solicitud_web(carlos, {
            'servicio': servicio('tienda-online'),
            'titulo': 'Tienda online Ferretería El Faro',
            'tipo_sitio': 'tienda',
            'tiene_sitio_actual': 'si',
            'url_sitio_actual': 'https://ferreteriaelfaro.cl',
            'nombre_negocio': 'Ferretería El Faro',
            'rubro': 'comercio',
            'descripcion_negocio': 'Ferretería de barrio con más de 800 productos. Queremos vender en línea con retiro en tienda y despacho local.',
            'publico_objetivo': 'Vecinos de Talcahuano y maestros de la construcción',
            'objetivos': ['vender', 'clientes'],
            'funcionalidades': ['catalogo', 'tienda', 'login'],
            'integraciones': ['pagos', 'whatsapp'],
            'num_paginas': 8,
            'complejidad': 'alta',
            'tiene_contenido': False,
            'estilo_visual': 'moderno',
            'colores': 'Rojo y blanco',
            'secciones': ['inicio', 'productos', 'preguntas', 'contacto'],
            'situacion_logo': 'mejorar',
            'dominio': 'ferreteriaelfaro.cl',
            'presupuesto': 'mas_1000',
            'medio_contacto': 'correo',
        })
        gestion.asignar_responsable(tienda, benjamin, admin)
        gestion.cambiar_estado(tienda, estado(EstadoSolicitud.EN_REVISION), benjamin, 'Revisando el catálogo y las formas de despacho.', notificar=False)
        self._cotizar(tienda, admin, [
            ('Tienda online: diseño, catálogo y carrito de compras', 1, 980000),
            ('Carga inicial de productos', 100, 1500),
            ('Cuentas de cliente e historial de pedidos', 1, 225000),
            ('Integración con Webpay', 1, 300000),
        ], 35, 20, 'Incluye catálogo inicial de 100 productos, carro de compras, cuentas de cliente, pago con Webpay y capacitación para administrar pedidos.')
        gestion.responder_cotizacion(tienda, 'aceptada', 'Nos parece bien, ¿cuándo empezamos?', carlos)
        gestion.cambiar_estado(tienda, estado(EstadoSolicitud.EN_DESARROLLO), benjamin, 'Comenzamos el desarrollo de la tienda.', notificar=False)
        self._fechar(tienda, ahora - timedelta(days=58), [5, 40, 64, 90])
        self._mensaje(tienda, carlos, 'Les envío por aquí la planilla con los productos más vendidos para priorizarlos en el catálogo.', ahora - timedelta(days=52))
        self._mensaje(tienda, benjamin, 'Recibida, gracias Carlos. Partiremos con esos productos y la próxima semana te mostramos un avance.', ahora - timedelta(days=51, hours=20))

        mantenimiento = gestion.crear_solicitud(paula, Servicio.TIPO_MANTENIMIENTO, {
            'servicio': servicio('mantenimiento-mensual'),
            'titulo': 'Plan de mantenimiento mensual',
            'descripcion': 'Necesitamos respaldos y actualizaciones periódicas del sitio de la fundación.',
            'url_sitio': 'https://fundacionvida.cl',
        }, detalles={'Plataforma': 'WordPress', 'Frecuencia': 'Mensual', 'Tareas': ['Respaldos periódicos', 'Actualizaciones de seguridad', 'Informe mensual de estado']})
        gestion.asignar_responsable(mantenimiento, franco, admin)
        gestion.cambiar_estado(mantenimiento, estado(EstadoSolicitud.EN_REVISION), franco, 'Estamos revisando la versión de WordPress y los complementos instalados.', notificar=False)
        self._fechar(mantenimiento, ahora - timedelta(days=20), [9])

        web = gestion.crear_solicitud_web(maria, {
            'servicio': servicio('sitio-con-reservas'),
            'titulo': 'Sitio web para Cafetería Aroma',
            'tipo_sitio': 'servicios',
            'tiene_sitio_actual': 'no',
            'nombre_negocio': 'Cafetería Aroma',
            'rubro': 'gastronomia',
            'descripcion_negocio': 'Cafetería de especialidad en el centro de Concepción. Queremos mostrar la carta, la ubicación y que los clientes puedan reservar mesa.',
            'publico_objetivo': 'Estudiantes y profesionales del centro de Concepción',
            'objetivos': ['presencia', 'mostrar', 'reservas'],
            'funcionalidades': ['formulario', 'galeria', 'catalogo', 'reservas'],
            'integraciones': ['whatsapp', 'redes', 'mapa'],
            'num_paginas': 6,
            'complejidad': 'media',
            'tiene_contenido': True,
            'fecha_deseada': timezone.localdate() + timedelta(days=45),
            'observaciones': 'Nos gustaría usar los colores de nuestro logo.',
            'estilo_visual': 'elegante',
            'colores': 'Café, crema y verde oliva',
            'secciones': ['inicio', 'nosotros', 'productos', 'reservas', 'galeria', 'contacto'],
            'situacion_logo': 'tiene',
            'sitios_referencia': 'https://www.starbucks.cl',
            'dominio': 'cafeteriaaroma.cl',
            'presupuesto': '300_600',
            'medio_contacto': 'whatsapp',
        })
        gestion.asignar_responsable(web, benjamin, admin)
        gestion.cambiar_estado(web, estado(EstadoSolicitud.EN_REVISION), benjamin, 'Estamos revisando tus requerimientos.', notificar=False)
        self._cotizar(web, admin, [
            ('Sitio con reservas: diseño y desarrollo de 6 páginas', 1, 430000),
            ('Carta digital y galería de productos', 1, 170000),
            ('Sistema de reservas de mesa en línea', 1, 225000),
            ('Integración con WhatsApp, redes sociales y Google Maps', 1, 60000),
            ('Publicación, dominio .cl por un año y capacitación', 1, 100000),
        ], 25, 15, 'Sitio de 6 páginas con carta digital, galería, reservas en línea, mapa y botón de WhatsApp. Incluye publicación, dominio .cl por un año y una capacitación de 1 hora. Forma de pago: 50% al aceptar y 50% contra entrega.')
        self._fechar(web, ahora - timedelta(days=5), [3, 27])
        self._mensaje(web, maria, '¿Pueden usar las fotos de nuestro Instagram para la galería?', ahora - timedelta(days=4, hours=12))
        self._mensaje(web, benjamin, 'Sí, María. Si nos compartes el acceso o las fotos en buena resolución, las optimizamos para la web sin costo adicional.', ahora - timedelta(days=4, hours=9), leido=False)

        atrasada = gestion.crear_solicitud(paula, Servicio.TIPO_SOPORTE, {
            'servicio': servicio('soporte-tecnico'),
            'titulo': 'El formulario de donaciones no envía correos',
            'descripcion': 'Desde la última actualización el formulario muestra un mensaje de éxito, pero los correos no llegan.',
            'url_sitio': 'https://fundacionvida.cl',
        }, detalles={'Tipo de problema': 'Problemas con correos o formularios', 'Ocurre desde': 'Hace tres días'}, prioridad='alta')
        self._fechar(atrasada, ahora - timedelta(hours=30), [])

        soporte_relacionado = gestion.crear_solicitud(maria, Servicio.TIPO_SOPORTE, {
            'servicio': servicio('soporte-tecnico'),
            'titulo': 'El blog muestra un error al publicar',
            'descripcion': 'Desde ayer, al intentar publicar una entrada nueva aparece un mensaje de error y no se guarda.',
            'url_sitio': 'https://blog.cafeteriaaroma.cl',
            'relacionada': mejora,
        }, detalles={'Tipo de problema': 'Errores o funciones que no responden', 'Ocurre desde': 'Ayer en la tarde'}, prioridad='urgente')
        gestion.asignar_responsable(soporte_relacionado, franco, admin)
        gestion.cambiar_estado(soporte_relacionado, estado(EstadoSolicitud.EN_REVISION), franco, 'Estamos revisando el registro de errores del servidor.', notificar=False)
        self._fechar(soporte_relacionado, ahora - timedelta(hours=26), [2])
        self._mensaje(soporte_relacionado, maria, 'Adjunto el mensaje exacto que aparece: "Error al guardar la entrada".', ahora - timedelta(hours=25), leido=False)

        clinica = gestion.crear_solicitud_web(andrea, {
            'servicio': servicio('sitio-con-reservas'),
            'titulo': 'Sitio con agenda de horas para clínica dental',
            'tipo_sitio': 'servicios',
            'tiene_sitio_actual': 'no',
            'nombre_negocio': 'Clínica Dental Sonríe',
            'rubro': 'salud',
            'descripcion_negocio': 'Clínica dental familiar con tres especialistas. Queremos que los pacientes reserven horas en línea y conozcan los tratamientos.',
            'publico_objetivo': 'Familias de Chiguayante y Concepción',
            'objetivos': ['presencia', 'reservas', 'informar'],
            'funcionalidades': ['formulario', 'reservas', 'galeria'],
            'integraciones': ['whatsapp', 'mapa', 'analitica'],
            'num_paginas': 7,
            'complejidad': 'media',
            'tiene_contenido': False,
            'estilo_visual': 'minimalista',
            'colores': 'Celeste y blanco',
            'secciones': ['inicio', 'servicios', 'reservas', 'preguntas', 'contacto'],
            'situacion_logo': 'crear',
            'presupuesto': 'por_definir',
            'medio_contacto': 'correo',
        })
        self._fechar(clinica, ahora - timedelta(hours=2), [])

    # Conversaciones de ejemplo con el asistente.
    def _crear_consultas(self, clientes):
        for indice, texto in enumerate(CONSULTAS):
            usuario = clientes[indice % len(clientes)] if indice % 3 == 0 else None
            resultado = AsistenteVirtual(usuario).responder(texto)
            fecha = timezone.now() - timedelta(days=len(CONSULTAS) - indice, hours=indice)
            creados = MensajeAsistente.objects.bulk_create([
                MensajeAsistente(usuario=usuario, sesion=f'demo-{indice}', contenido=texto),
                MensajeAsistente(usuario=usuario, sesion=f'demo-{indice}', contenido=resultado['respuesta'], es_asistente=True, intencion=resultado['intencion']),
            ])
            MensajeAsistente.objects.filter(pk__in=[m.pk for m in creados if m.pk]).update(fecha=fecha)
