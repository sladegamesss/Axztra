from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.test.utils import override_settings
from django.utils import timezone

from plataforma import gestion
from plataforma.forms import CotizacionForm
from plataforma.models import EstadoSolicitud, PerfilCliente, Servicio

User = get_user_model()

ADMIN = {'email': 'admin@axztra.cl', 'password': 'AxztraAdmin2026', 'first_name': 'Camilo', 'last_name': 'Barra'}
CLIENTES = [
    {'email': 'cliente@axztra.cl', 'password': 'Cliente2026', 'first_name': 'María', 'last_name': 'González', 'empresa': 'Cafetería Aroma', 'ciudad': 'Concepción'},
    {'email': 'carlos.perez@axztra.cl', 'password': 'Cliente2026', 'first_name': 'Carlos', 'last_name': 'Pérez', 'empresa': 'Ferretería El Faro', 'ciudad': 'Talcahuano'},
    {'email': 'fundacion.vida@axztra.cl', 'password': 'Cliente2026', 'first_name': 'Paula', 'last_name': 'Muñoz', 'empresa': 'Fundación Vida', 'ciudad': 'Hualpén'},
]


class Command(BaseCommand):
    help = 'Crea usuarios y solicitudes de demostración para presentar la plataforma.'

    def add_arguments(self, parser):
        parser.add_argument('--reiniciar', action='store_true', help='Elimina las solicitudes de los clientes de demostración antes de crearlas de nuevo.')

    def _usuario(self, datos, staff=False):
        usuario, creado = User.objects.get_or_create(
            username=datos['email'],
            defaults={
                'email': datos['email'],
                'first_name': datos['first_name'],
                'last_name': datos['last_name'],
                'is_staff': staff,
                'is_superuser': staff,
            },
        )
        if creado:
            usuario.set_password(datos['password'])
            usuario.save()
        if not staff:
            PerfilCliente.objects.update_or_create(
                usuario=usuario,
                defaults={'empresa': datos.get('empresa', ''), 'ciudad': datos.get('ciudad', ''), 'telefono': '+56 9 5555 0000'},
            )
        return usuario, creado

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.dummy.EmailBackend')
    def handle(self, *args, **opciones):
        with transaction.atomic():
            admin, admin_creado = self._usuario(ADMIN, staff=True)
            clientes = [self._usuario(datos)[0] for datos in CLIENTES]

            if opciones['reiniciar']:
                for cliente in clientes:
                    cliente.solicitudes.all().delete()

            if any(cliente.solicitudes.exists() for cliente in clientes):
                self.stdout.write(self.style.WARNING('Los clientes de demostración ya tienen solicitudes. Usa --reiniciar para regenerarlas.'))
            else:
                self._crear_solicitudes(admin, clientes)

        self.stdout.write(self.style.SUCCESS('Datos de demostración listos.'))
        self.stdout.write(f"  Administrador: {ADMIN['email']} / {ADMIN['password']}" + ('' if admin_creado else ' (ya existía, se mantuvo su contraseña)'))
        self.stdout.write(f"  Cliente:       {CLIENTES[0]['email']} / {CLIENTES[0]['password']}")

    def _crear_solicitudes(self, admin, clientes):
        maria, carlos, paula = clientes
        estado = EstadoSolicitud.obtener

        web = gestion.crear_solicitud_web(maria, {
            'servicio': Servicio.objects.filter(slug='sitio-con-reservas').first(),
            'titulo': 'Sitio web para Cafetería Aroma',
            'tipo_sitio': 'servicios',
            'tiene_sitio_actual': 'no',
            'url_sitio_actual': '',
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
        })
        gestion.cambiar_estado(web, estado(EstadoSolicitud.EN_REVISION), admin, 'Estamos revisando tus requerimientos.')
        formulario = CotizacionForm({'monto': 890000, 'plazo_dias': 25, 'validez_dias': 15, 'detalle': 'Sitio de 6 páginas con carta digital, galería, reservas en línea, mapa y botón de WhatsApp. Incluye publicación y capacitación.'})
        formulario.is_valid()
        gestion.emitir_cotizacion(web, formulario, admin)

        tienda = gestion.crear_solicitud_web(carlos, {
            'servicio': Servicio.objects.filter(slug='tienda-online').first(),
            'titulo': 'Tienda online Ferretería El Faro',
            'tipo_sitio': 'tienda',
            'tiene_sitio_actual': 'no',
            'url_sitio_actual': '',
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
            'fecha_deseada': None,
            'observaciones': '',
        })
        gestion.cambiar_estado(tienda, estado(EstadoSolicitud.EN_REVISION), admin)
        formulario = CotizacionForm({'monto': 1650000, 'plazo_dias': 35, 'validez_dias': 20, 'detalle': 'Tienda con catálogo inicial de 100 productos, carro de compras, cuentas de cliente e integración con Webpay.'})
        formulario.is_valid()
        gestion.emitir_cotizacion(tienda, formulario, admin)
        gestion.responder_cotizacion(tienda, 'aceptada', 'Nos parece bien, ¿cuándo empezamos?', carlos)
        gestion.cambiar_estado(tienda, estado(EstadoSolicitud.EN_DESARROLLO), admin, 'Comenzamos el desarrollo de la tienda.')

        gestion.crear_solicitud(paula, Servicio.TIPO_SOPORTE, {
            'servicio': Servicio.objects.filter(slug='soporte-tecnico').first(),
            'titulo': 'El formulario de donaciones no envía correos',
            'descripcion': 'Desde la última actualización el formulario muestra un mensaje de éxito pero no llegan los correos.',
            'url_sitio': 'https://fundacionvida.cl',
        }, detalles={'Tipo de problema': 'Problemas con correos o formularios', 'Ocurre desde': 'Hace tres días'}, prioridad='alta')

        mantenimiento = gestion.crear_solicitud(paula, Servicio.TIPO_MANTENIMIENTO, {
            'servicio': Servicio.objects.filter(slug='mantenimiento-mensual').first(),
            'titulo': 'Plan de mantenimiento mensual',
            'descripcion': 'Necesitamos respaldos y actualizaciones periódicas.',
            'url_sitio': 'https://fundacionvida.cl',
        }, detalles={'Plataforma': 'WordPress', 'Frecuencia': 'Mensual', 'Tareas': ['Respaldos periódicos', 'Actualizaciones de seguridad']})
        gestion.cambiar_estado(mantenimiento, estado(EstadoSolicitud.EN_REVISION), admin)

        mejora = gestion.crear_solicitud(maria, Servicio.TIPO_MEJORA, {
            'servicio': Servicio.objects.filter(slug='optimizacion-velocidad-seo').first(),
            'titulo': 'Mejorar velocidad del blog personal',
            'descripcion': 'El blog tarda mucho en cargar desde el celular.',
            'url_sitio': 'https://blogaroma.cl',
        }, detalles={'Mejoras solicitadas': ['Mejorar velocidad de carga', 'Posicionamiento en buscadores (SEO)']})
        gestion.cambiar_estado(mejora, estado(EstadoSolicitud.EN_REVISION), admin)
        gestion.cambiar_estado(mejora, estado(EstadoSolicitud.COMPLETADA), admin, 'Optimización terminada. El sitio carga en menos de 2 segundos.')
