"""
Pruebas automáticas de AXZTRA.

Se ejecutan con: python manage.py test plataforma
Cada clase agrupa las pruebas de una parte del sistema; entre paréntesis, los casos de uso o requisitos que cubre.
"""

import json
import os
import re
import shutil
import tempfile
import uuid
from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.models import ProtectedError
from django.conf import settings
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from .asistente import AsistenteVirtual
from .estimacion import calcular_estimacion
from .forms import validar_rut, validar_telefono
from .gestion import guardar_adjunto, registrar_historial
from .models import (
    Adjunto,
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
from .verificacion import CLAVE_SESION_VERIFICADA

User = get_user_model()
MEDIA_PRUEBAS = tempfile.mkdtemp(prefix='axztra-pruebas-')

DATOS_WEB = {
    'titulo': 'Sitio para mi cafetería',
    'tipo_sitio': 'corporativo',
    'tiene_sitio_actual': 'no',
    'url_sitio_actual': '',
    'nombre_negocio': 'Cafetería Aroma',
    'rubro': 'gastronomia',
    'descripcion_negocio': 'Cafetería de especialidad en Concepción.',
    'publico_objetivo': 'Estudiantes',
    'objetivos': ['presencia', 'mostrar'],
    'funcionalidades': ['formulario', 'galeria'],
    'integraciones': ['whatsapp', 'mapa'],
    'num_paginas': '7',
    'complejidad': 'media',
    'tiene_contenido': 'on',
    'fecha_deseada': '',
    'observaciones': 'Usar colores del logo.',
}


def crear_cliente(email='cliente@correo.cl', password='ClaveSegura2026', nombre='Ana'):
    usuario = User.objects.create_user(username=email, email=email, password=password, first_name=nombre, last_name='Rojas')
    PerfilCliente.objects.create(usuario=usuario, empresa='Empresa de prueba')
    return usuario


def crear_staff(email='admin@axztra.cl', password='ClaveAdmin2026', superusuario=True, nombre='Camilo'):
    return User.objects.create_user(
        username=email, email=email, password=password, first_name=nombre, last_name='Barra',
        is_staff=True, is_superuser=superusuario,
    )


def codigo_desde_correo():
    for mensaje in reversed(mail.outbox):
        encontrado = re.search(r'^\s+(\d{6})\s*$', mensaje.body, re.MULTILINE)
        if encontrado:
            return encontrado.group(1)
    return None


def verificar_sesion(cliente_http, usuario):
    cliente_http.force_login(usuario)
    sesion = cliente_http.session
    sesion[CLAVE_SESION_VERIFICADA] = usuario.pk
    sesion.save()


def nueva_solicitud(cliente, tipo=Servicio.TIPO_SOPORTE, titulo='Error en el formulario', prioridad='media', **extra):
    return Solicitud.objects.create(
        cliente=cliente, tipo=tipo, titulo=titulo, descripcion='Detalle de la solicitud.', prioridad=prioridad, **extra
    )


# Base común: borra la caché antes de cada prueba.
class BaseTest(TestCase):
    def setUp(self):
        cache.clear()


# Fórmula de estimación (RF05, CU02, sección 3.5).
class EstimacionTests(BaseTest):
    def test_formula_con_factor_de_complejidad(self):
        r = calcular_estimacion('corporativo', 'media', 7, ['formulario', 'galeria'], ['whatsapp', 'mapa'])
        self.assertEqual(r['total'], 300000 + 75000 + 50000 + 62500 + 18750 + 25000)
        self.assertEqual(r['monto_minimo'], 480000)
        self.assertEqual(r['monto_maximo'], 610000)
        self.assertEqual((r['semanas_minimas'], r['semanas_maximas']), (3, 5))

    def test_complejidad_basica_sin_extras(self):
        r = calcular_estimacion('landing', 'basica', 1, [], [])
        self.assertEqual(r['total'], 220000)
        self.assertEqual(len(r['desglose']), 1)

    def test_tienda_y_muchas_paginas_suman_semanas(self):
        r = calcular_estimacion('tienda', 'alta', 20, ['tienda'], ['pagos'])
        self.assertEqual((r['semanas_minimas'], r['semanas_maximas']), (6, 10))

    def test_valores_fuera_de_rango_se_normalizan(self):
        r = calcular_estimacion('desconocido', 'extrema', 'abc', ['formulario', 'inventada'], ['pagos'])
        self.assertGreater(r['total'], 0)
        self.assertNotIn('inventada', json.dumps(r['desglose']))


# Validaciones de RUT, teléfono, fechas y archivos.
class ValidacionesTests(BaseTest):
    def test_rut_valido_se_formatea(self):
        self.assertEqual(validar_rut('12345678-5'), '12.345.678-5')
        self.assertEqual(validar_rut('7.654.321-6'), '7.654.321-6')

    def test_rut_invalido(self):
        from django import forms

        with self.assertRaises(forms.ValidationError):
            validar_rut('12345678-9')

    def test_telefono(self):
        from django import forms

        self.assertEqual(validar_telefono('+56 9 1234 5678'), '+56 9 1234 5678')
        with self.assertRaises(forms.ValidationError):
            validar_telefono('123')


# Páginas públicas, menú, barra móvil y cabeceras de seguridad (CU01).
class PaginasPublicasTests(BaseTest):
    def test_paginas_publicas_responden(self):
        for nombre in ['inicio', 'catalogo', 'nosotros', 'terminos', 'privacidad', 'login', 'registro', 'recuperar_clave']:
            with self.subTest(pagina=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)

    def test_menu_con_boton_inicio_visible(self):
        respuesta = self.client.get(reverse('catalogo'))
        self.assertContains(respuesta, 'class="enlace-inicio" href="/"')
        self.assertContains(respuesta, 'class="inicio-movil" href="/"')
        portada = self.client.get(reverse('inicio'))
        self.assertContains(portada, 'class="enlace-inicio" href="/" aria-current="page"')

    def test_accesos_faciles_para_todo_publico(self):
        respuesta = self.client.get(reverse('catalogo'))
        self.assertContains(respuesta, 'class="barra-movil"')
        self.assertContains(respuesta, 'data-tamano-texto')
        self.assertContains(respuesta, 'data-texto-opcion="muy-grande"')
        self.assertContains(respuesta, 'js/carga-temprana.js')
        self.assertNotContains(respuesta, 'class="whatsapp"')
        self.assertNotContains(respuesta, 'id="asistente-ventana"')
        self.assertNotContains(self.client.get(reverse('inicio')), 'id="asistente-ventana"')
        self.client.force_login(crear_cliente())
        respuesta = self.client.get(reverse('crear_web'))
        self.assertContains(respuesta, '<i class="fa-solid fa-house" aria-hidden="true"></i> Inicio</a></li>')
        self.assertContains(respuesta, 'Mis solicitudes</span>')
        self.assertContains(respuesta, 'id="asistente-ventana"')
        for nombre in ('nueva_solicitud', 'solicitar_mejora', 'solicitar_soporte', 'solicitar_mantenimiento'):
            self.assertContains(self.client.get(reverse(nombre)), 'id="asistente-ventana"')
        self.assertNotContains(self.client.get(reverse('mis_solicitudes')), 'id="asistente-ventana"')

    def test_cabeceras_de_seguridad(self):
        respuesta = self.client.get(reverse('inicio'))
        self.assertIn("script-src 'self'", respuesta['Content-Security-Policy'])
        self.assertIn("frame-ancestors 'none'", respuesta['Content-Security-Policy'])
        self.assertEqual(respuesta['X-Frame-Options'], 'DENY')
        self.assertEqual(respuesta['X-Content-Type-Options'], 'nosniff')
        self.assertIn('camera=()', respuesta['Permissions-Policy'])

    def test_paginas_privadas_no_se_guardan_en_cache(self):
        verificar_sesion(self.client, crear_cliente())
        respuesta = self.client.get(reverse('mis_solicitudes'))
        self.assertIn('no-store', respuesta['Cache-Control'])

    def test_estimador_de_portada_incluye_configuracion(self):
        respuesta = self.client.get(reverse('inicio'))
        self.assertContains(respuesta, 'id="config-estimacion"')
        self.assertContains(respuesta, 'id="estimador-portada"')

    def test_detalle_de_servicio_e_inactivo(self):
        servicio = Servicio.objects.get(slug='landing-page')
        self.assertContains(self.client.get(servicio.get_absolute_url()), servicio.nombre)
        servicio.activo = False
        servicio.save()
        self.assertEqual(self.client.get(servicio.get_absolute_url()).status_code, 404)

    def test_filtros_del_catalogo(self):
        respuesta = self.client.get(reverse('catalogo'), {'tipo': 'Soporte'})
        self.assertContains(respuesta, 'Soporte técnico por incidencia')
        self.assertNotContains(respuesta, 'Tienda online</a>')
        respuesta = self.client.get(reverse('catalogo'), {'q': 'zzzzzz'})
        self.assertContains(respuesta, 'No encontramos servicios')

    def test_cambios_del_catalogo_se_ven_de_inmediato(self):
        self.client.get(reverse('inicio'))
        Servicio.objects.filter(slug='landing-page').update(destacado=False)
        servicio = Servicio.objects.get(slug='landing-page')
        servicio.nombre = 'Landing page renovada'
        servicio.destacado = True
        servicio.save()
        self.assertContains(self.client.get(reverse('inicio')), 'Landing page renovada')

    def test_pagina_404_personalizada(self):
        respuesta = self.client.get('/no-existe/')
        self.assertEqual(respuesta.status_code, 404)
        self.assertContains(respuesta, 'No encontramos esta página', status_code=404)

    def test_robots_sitemap_y_salud(self):
        robots = self.client.get('/robots.txt')
        self.assertContains(robots, 'Disallow: /panel/')
        self.assertContains(robots, 'sitemap.xml')
        sitemap = self.client.get('/sitemap.xml')
        self.assertContains(sitemap, '/servicios/landing-page/')
        salud = self.client.get(reverse('salud'))
        self.assertEqual(salud.json()['estado'], 'ok')

    def test_rutas_privadas_piden_sesion(self):
        for nombre in ['mis_solicitudes', 'nueva_solicitud', 'crear_web', 'mi_cuenta', 'panel_inicio']:
            with self.subTest(ruta=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 302)

    def test_portada_con_pocas_consultas(self):
        self.client.get(reverse('inicio'))
        with self.assertNumQueries(0):
            self.client.get(reverse('inicio'))


# Registro, inicio de sesión, bloqueo y cuenta del cliente (CU04, CU05, CU06, CU14).
class CuentasTests(BaseTest):
    def _registro(self, **cambios):
        datos = {
            'first_name': 'Ana', 'last_name': 'Rojas', 'email': 'Ana@Correo.cl', 'empresa': 'Aroma',
            'telefono': '+56 9 1111 2222', 'password1': 'ClaveSegura2026', 'password2': 'ClaveSegura2026',
            'acepta_terminos': 'on',
        }
        datos.update(cambios)
        return self.client.post(reverse('registro'), datos)

    def test_registro_crea_usuario_y_confirma_el_correo_con_codigo(self):
        respuesta = self._registro()
        self.assertRedirects(respuesta, reverse('verificar_codigo'))
        usuario = User.objects.get(email='ana@correo.cl')
        self.assertEqual(usuario.perfil_cliente.empresa, 'Aroma')
        self.assertIsNotNone(usuario.perfil_cliente.fecha_aceptacion_terminos)
        self.assertEqual(len(mail.outbox), 2)
        self.assertNotIn('_auth_user_id', self.client.session)
        respuesta = self.client.post(reverse('verificar_codigo'), {'codigo': codigo_desde_correo()})
        self.assertRedirects(respuesta, reverse('nueva_solicitud'))
        self.assertEqual(self.client.get(reverse('mis_solicitudes')).status_code, 200)

    def test_registro_exige_aceptar_terminos(self):
        respuesta = self._registro(acepta_terminos='')
        self.assertContains(respuesta, 'Debes aceptar los términos')
        self.assertFalse(User.objects.filter(email='ana@correo.cl').exists())

    def test_registro_rechaza_correo_duplicado(self):
        crear_cliente('ana@correo.cl')
        self.assertContains(self._registro(), 'Ya existe una cuenta con este correo')

    def test_registro_respeta_destino_seguro(self):
        destino = reverse('crear_web') + '?tipo_sitio=tienda'
        self.assertRedirects(self._registro(next=destino), reverse('verificar_codigo'))
        respuesta = self.client.post(reverse('verificar_codigo'), {'codigo': codigo_desde_correo()})
        self.assertRedirects(respuesta, destino, fetch_redirect_response=False)

    def test_login_y_destino_inseguro(self):
        crear_cliente()
        respuesta = self.client.post(reverse('login'), {'email': 'CLIENTE@correo.cl', 'password': 'ClaveSegura2026', 'next': 'https://sitio-malicioso.com/'})
        self.assertRedirects(respuesta, reverse('verificar_codigo'))
        respuesta = self.client.post(reverse('verificar_codigo'), {'codigo': codigo_desde_correo()})
        self.assertRedirects(respuesta, reverse('inicio'))

    def test_login_incorrecto(self):
        crear_cliente()
        respuesta = self.client.post(reverse('login'), {'email': 'cliente@correo.cl', 'password': 'otra'})
        self.assertContains(respuesta, 'El correo o la contraseña no son correctos')

    def test_bloqueo_tras_intentos_fallidos(self):
        crear_cliente()
        for _ in range(5):
            self.client.post(reverse('login'), {'email': 'cliente@correo.cl', 'password': 'incorrecta'})
        respuesta = self.client.post(reverse('login'), {'email': 'cliente@correo.cl', 'password': 'ClaveSegura2026'})
        self.assertContains(respuesta, 'demasiados intentos fallidos')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_solo_por_post(self):
        self.client.force_login(crear_cliente())
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.client.post(reverse('logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_actualizar_mis_datos(self):
        usuario = crear_cliente()
        self.client.force_login(usuario)
        respuesta = self.client.post(reverse('mi_cuenta'), {
            'first_name': 'Ana María', 'last_name': 'Rojas', 'empresa': 'Nueva', 'rut': '12345678-5',
            'telefono': '+56 9 1234 5678', 'ciudad': 'Hualpén', 'recibir_notificaciones': 'on',
        })
        self.assertRedirects(respuesta, reverse('mi_cuenta'))
        usuario.refresh_from_db()
        self.assertEqual(usuario.first_name, 'Ana María')
        self.assertEqual(usuario.perfil_cliente.rut, '12.345.678-5')

    def test_cambiar_contrasena_mantiene_la_sesion(self):
        usuario = crear_cliente()
        self.client.force_login(usuario)
        respuesta = self.client.post(reverse('cambiar_clave'), {
            'old_password': 'ClaveSegura2026', 'new_password1': 'OtraClave2027x', 'new_password2': 'OtraClave2027x',
        })
        self.assertRedirects(respuesta, reverse('mi_cuenta'))
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password('OtraClave2027x'))
        self.assertEqual(self.client.get(reverse('mi_cuenta')).status_code, 200)

    def test_descargar_mis_datos(self):
        usuario = crear_cliente()
        nueva_solicitud(usuario, titulo='Solicitud exportable')
        self.client.force_login(usuario)
        respuesta = self.client.get(reverse('descargar_datos'))
        self.assertEqual(respuesta['Content-Type'], 'application/json; charset=utf-8')
        datos = json.loads(respuesta.content)
        self.assertEqual(datos['cuenta']['correo'], 'cliente@correo.cl')
        self.assertEqual(datos['solicitudes'][0]['titulo'], 'Solicitud exportable')

    def test_eliminar_cuenta(self):
        usuario = crear_cliente()
        solicitud = nueva_solicitud(usuario)
        self.client.force_login(usuario)
        respuesta = self.client.post(reverse('eliminar_cuenta'), {'password': 'ClaveSegura2026'})
        self.assertContains(respuesta, 'cancela o finaliza tus solicitudes')
        solicitud.estado = EstadoSolicitud.obtener(EstadoSolicitud.COMPLETADA)
        solicitud.save()
        respuesta = self.client.post(reverse('eliminar_cuenta'), {'password': 'ClaveSegura2026'})
        self.assertRedirects(respuesta, reverse('inicio'))
        usuario.refresh_from_db()
        self.assertFalse(usuario.is_active)
        self.assertTrue(usuario.email.endswith('.invalid'))
        self.assertEqual(usuario.perfil_cliente.telefono, '')
        self.assertTrue(Solicitud.objects.filter(pk=solicitud.pk).exists())

    def test_recuperar_contrasena_envia_correo_y_limita(self):
        crear_cliente()
        respuesta = self.client.post(reverse('recuperar_clave'), {'email': 'cliente@correo.cl'})
        self.assertRedirects(respuesta, reverse('recuperar_enviado'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/cuenta/recuperar/', mail.outbox[0].body)
        for _ in range(5):
            respuesta = self.client.post(reverse('recuperar_clave'), {'email': 'cliente@correo.cl'})
        self.assertEqual(respuesta.status_code, 429)


# Verificación en dos pasos de clientes y equipo (CU07, RNF04).
class DosFactoresTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.staff = crear_staff()

    def _ingresar(self):
        return self.client.post(reverse('login'), {'email': 'admin@axztra.cl', 'password': 'ClaveAdmin2026'})

    def test_staff_requiere_codigo_y_luego_accede_al_panel(self):
        self.assertRedirects(self._ingresar(), reverse('verificar_codigo'))
        self.assertNotIn('_auth_user_id', self.client.session)
        respuesta = self.client.post(reverse('verificar_codigo'), {'codigo': codigo_desde_correo()})
        self.assertRedirects(respuesta, reverse('panel_inicio'))
        self.assertEqual(self.client.get(reverse('panel_inicio')).status_code, 200)
        self.assertTrue(RegistroActividad.objects.filter(accion='acceso', usuario=self.staff).exists())

    def test_cliente_requiere_codigo_para_entrar(self):
        cliente = crear_cliente()
        respuesta = self.client.post(reverse('login'), {'email': 'cliente@correo.cl', 'password': 'ClaveSegura2026'})
        self.assertRedirects(respuesta, reverse('verificar_codigo'))
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.get(reverse('mis_solicitudes')).status_code, 302)
        respuesta = self.client.post(reverse('verificar_codigo'), {'codigo': codigo_desde_correo()})
        self.assertRedirects(respuesta, reverse('inicio'))
        self.assertEqual(self.client.get(reverse('mis_solicitudes')).status_code, 200)
        self.assertFalse(RegistroActividad.objects.filter(accion='acceso', usuario=cliente).exists())

    def test_cliente_con_codigo_incorrecto_no_inicia_sesion(self):
        crear_cliente()
        self.client.post(reverse('login'), {'email': 'cliente@correo.cl', 'password': 'ClaveSegura2026'})
        respuesta = self.client.post(reverse('verificar_codigo'), {'codigo': '000000'})
        self.assertContains(respuesta, 'Código incorrecto')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_cliente_no_entra_al_panel_con_su_codigo(self):
        crear_cliente()
        self.client.post(reverse('login'), {'email': 'cliente@correo.cl', 'password': 'ClaveSegura2026'})
        self.client.post(reverse('verificar_codigo'), {'codigo': codigo_desde_correo()})
        self.assertRedirects(self.client.get(reverse('panel_inicio')), reverse('inicio'), fetch_redirect_response=False)

    def test_verificacion_de_clientes_se_puede_desactivar(self):
        crear_cliente()
        with override_settings(AXZTRA={**settings.AXZTRA, 'VERIFICACION_CLIENTES': False}):
            respuesta = self.client.post(reverse('login'), {'email': 'cliente@correo.cl', 'password': 'ClaveSegura2026'})
            self.assertRedirects(respuesta, reverse('inicio'))
            self.assertEqual(self.client.get(reverse('mis_solicitudes')).status_code, 200)

    def test_codigo_incorrecto_y_limite_de_intentos(self):
        self._ingresar()
        for _ in range(5):
            respuesta = self.client.post(reverse('verificar_codigo'), {'codigo': '000000'})
        self.assertContains(respuesta, 'Solicita un código nuevo')
        respuesta = self.client.post(reverse('verificar_codigo'), {'codigo': codigo_desde_correo()})
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_codigo_expirado(self):
        self._ingresar()
        CodigoVerificacion.objects.update(expira=timezone.now() - timedelta(minutes=1))
        respuesta = self.client.post(reverse('verificar_codigo'), {'codigo': codigo_desde_correo()})
        self.assertContains(respuesta, 'El código expiró')

    def test_sesion_sin_verificar_no_entra_al_panel_ni_al_admin(self):
        self.client.force_login(self.staff)
        self.assertRedirects(
            self.client.get(reverse('panel_inicio')),
            f"{reverse('verificar_codigo')}?next=%2Fpanel%2F",
            fetch_redirect_response=False,
        )
        self.assertEqual(self.client.get('/admin/').status_code, 302)

    def test_reenviar_codigo_invalida_el_anterior(self):
        self._ingresar()
        anterior = codigo_desde_correo()
        self.client.post(reverse('reenviar_codigo'))
        nuevo = codigo_desde_correo()
        if anterior != nuevo:
            respuesta = self.client.post(reverse('verificar_codigo'), {'codigo': anterior})
            self.assertEqual(respuesta.status_code, 200)
        respuesta = self.client.post(reverse('verificar_codigo'), {'codigo': nuevo})
        self.assertRedirects(respuesta, reverse('panel_inicio'))

    def test_cliente_no_accede_al_panel(self):
        self.client.force_login(crear_cliente())
        self.assertRedirects(self.client.get(reverse('panel_inicio')), reverse('inicio'))


# Formulario de cuatro pasos y estimación (CU08, CU09, CU02, DA-02).
@override_settings(MEDIA_ROOT=MEDIA_PRUEBAS)
class SolicitudWebTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.cliente = crear_cliente()
        self.client.force_login(self.cliente)
        self.staff = crear_staff()

    def test_flujo_completo_con_estimacion_y_aviso_al_equipo(self):
        datos = {**DATOS_WEB, 'token_envio': str(uuid.uuid4())}
        self.assertRedirects(self.client.post(reverse('crear_web'), datos), reverse('estimacion_web'))
        respuesta = self.client.get(reverse('estimacion_web'))
        self.assertContains(respuesta, '$480.000 a $610.000')
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post(reverse('estimacion_web'))
        solicitud = Solicitud.objects.get()
        self.assertRedirects(respuesta, solicitud.get_absolute_url())
        self.assertEqual(solicitud.estimacion.total, 531250)
        self.assertEqual(solicitud.requerimiento.funcionalidades, ['formulario', 'galeria'])
        self.assertEqual(solicitud.historial.count(), 1)
        destinatarios = {correo for m in mail.outbox for correo in m.to}
        self.assertIn('cliente@correo.cl', destinatarios)
        self.assertIn('admin@axztra.cl', destinatarios)

    def test_formulario_web_guarda_diseno_y_detalles(self):
        datos = {**DATOS_WEB, 'token_envio': str(uuid.uuid4()), 'estilo_visual': 'minimalista', 'colores': 'Azul y blanco',
                 'secciones': ['inicio', 'galeria', 'contacto'], 'situacion_logo': 'crear', 'dominio': 'https://www.MiCafe.cl/',
                 'sitios_referencia': 'https://ejemplo.cl\nhttps://otro.cl', 'presupuesto': '300_600', 'medio_contacto': 'whatsapp'}
        self.assertRedirects(self.client.post(reverse('crear_web'), datos), reverse('estimacion_web'))
        resumen = self.client.get(reverse('estimacion_web'))
        self.assertContains(resumen, 'Minimalista')
        self.assertContains(resumen, 'Entre $300.000 y $600.000')
        self.client.post(reverse('estimacion_web'))
        requerimiento = Solicitud.objects.get().requerimiento
        self.assertEqual(requerimiento.estilo_visual, 'minimalista')
        self.assertEqual(requerimiento.secciones, ['inicio', 'galeria', 'contacto'])
        self.assertEqual(requerimiento.dominio, 'micafe.cl')
        self.assertEqual(requerimiento.lista_referencias, ['https://ejemplo.cl', 'https://otro.cl'])
        detalle = self.client.get(requerimiento.solicitud.get_absolute_url())
        for texto in ('Necesito un logo nuevo', 'Inicio, Galería, Contacto', 'WhatsApp', 'https://otro.cl'):
            self.assertContains(detalle, texto)

    def test_formulario_web_usa_valores_por_defecto_y_valida_dominio(self):
        self.client.post(reverse('crear_web'), {**DATOS_WEB, 'token_envio': str(uuid.uuid4())})
        self.client.post(reverse('estimacion_web'))
        requerimiento = Solicitud.objects.get().requerimiento
        self.assertEqual((requerimiento.estilo_visual, requerimiento.situacion_logo, requerimiento.presupuesto, requerimiento.medio_contacto),
                         ('sin_preferencia', 'tiene', 'por_definir', 'correo'))
        respuesta = self.client.post(reverse('crear_web'), {**DATOS_WEB, 'dominio': 'esto no es un dominio'})
        self.assertContains(respuesta, 'Escribe un dominio válido')
        self.assertEqual(respuesta.context['paso_inicial'], 4)

    def test_envio_duplicado_no_crea_dos_solicitudes(self):
        token = str(uuid.uuid4())
        self.client.post(reverse('crear_web'), {**DATOS_WEB, 'token_envio': token})
        self.client.post(reverse('estimacion_web'))
        self.client.post(reverse('crear_web'), {**DATOS_WEB, 'token_envio': token})
        respuesta = self.client.post(reverse('estimacion_web'))
        self.assertEqual(Solicitud.objects.count(), 1)
        self.assertRedirects(respuesta, Solicitud.objects.get().get_absolute_url())

    def test_formulario_se_precarga_desde_el_estimador(self):
        respuesta = self.client.get(reverse('crear_web'), {'tipo_sitio': 'tienda', 'num_paginas': '12', 'funcionalidades': ['blog', 'inventada']})
        form = respuesta.context['form']
        self.assertEqual(form.initial['tipo_sitio'], 'tienda')
        self.assertEqual(form.initial['num_paginas'], 12)
        self.assertEqual(form.initial['funcionalidades'], ['blog'])

    def test_errores_vuelven_al_paso_correcto(self):
        respuesta = self.client.post(reverse('crear_web'), {**DATOS_WEB, 'objetivos': []})
        self.assertEqual(respuesta.context['paso_inicial'], 2)

    def test_sitio_actual_requiere_url(self):
        respuesta = self.client.post(reverse('crear_web'), {**DATOS_WEB, 'tiene_sitio_actual': 'si'})
        self.assertContains(respuesta, 'Indica la dirección de tu sitio actual')

    def test_fecha_en_pasado_no_se_acepta(self):
        ayer = (timezone.localdate() - timedelta(days=1)).isoformat()
        respuesta = self.client.post(reverse('crear_web'), {**DATOS_WEB, 'fecha_deseada': ayer})
        self.assertContains(respuesta, 'no puede estar en el pasado')

    def test_estimacion_sin_borrador_redirige(self):
        self.assertRedirects(self.client.get(reverse('estimacion_web')), reverse('crear_web'))

    def test_servicio_preseleccionado(self):
        servicio = Servicio.objects.get(slug='tienda-online')
        respuesta = self.client.get(reverse('crear_web'), {'servicio': servicio.pk})
        self.assertContains(respuesta, servicio.nombre)
        self.client.post(reverse('crear_web'), {**DATOS_WEB, 'servicio': servicio.pk})
        self.client.post(reverse('estimacion_web'))
        self.assertEqual(Solicitud.objects.get().servicio, servicio)


# Solicitudes de mejora, soporte y mantenimiento con archivos (CU08, CU10).
@override_settings(MEDIA_ROOT=MEDIA_PRUEBAS)
class SolicitudesSimplesTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.cliente = crear_cliente()
        self.client.force_login(self.cliente)

    def test_mejora_con_archivo_adjunto(self):
        archivo = SimpleUploadedFile('referencia.pdf', b'%PDF-1.4 contenido', content_type='application/pdf')
        respuesta = self.client.post(reverse('solicitar_mejora'), {
            'titulo': 'Rediseño', 'url_sitio': 'miempresa.cl', 'tipos_mejora': ['rediseno', 'seo'],
            'descripcion': 'Quiero un diseño moderno.', 'adjunto': archivo,
        })
        solicitud = Solicitud.objects.get()
        self.assertRedirects(respuesta, solicitud.get_absolute_url())
        self.assertEqual(solicitud.url_sitio, 'https://miempresa.cl')
        self.assertEqual(solicitud.detalles['Mejoras solicitadas'], ['Rediseño visual', 'Posicionamiento en buscadores (SEO)'])
        self.assertEqual(solicitud.adjuntos.get().nombre_original, 'referencia.pdf')

    def test_archivo_con_extension_no_permitida(self):
        archivo = SimpleUploadedFile('script.exe', b'MZ', content_type='application/octet-stream')
        respuesta = self.client.post(reverse('solicitar_soporte'), {
            'titulo': 'Caído', 'url_sitio': 'https://miempresa.cl', 'tipo_problema': 'caido', 'prioridad': 'urgente',
            'descripcion': 'No carga.', 'adjunto': archivo,
        })
        self.assertContains(respuesta, 'Formato no permitido')
        self.assertFalse(Solicitud.objects.exists())

    def test_soporte_con_prioridad(self):
        self.client.post(reverse('solicitar_soporte'), {
            'titulo': 'Sitio caído', 'url_sitio': 'https://miempresa.cl', 'tipo_problema': 'caido',
            'prioridad': 'urgente', 'desde_cuando': 'Hoy', 'descripcion': 'No carga.',
        })
        solicitud = Solicitud.objects.get()
        self.assertEqual(solicitud.prioridad, 'urgente')
        self.assertEqual(solicitud.horas_sla, 4)

    def test_mantenimiento(self):
        self.client.post(reverse('solicitar_mantenimiento'), {
            'titulo': 'Plan mensual', 'url_sitio': 'https://miempresa.cl', 'plataforma': 'wordpress',
            'frecuencia': 'mensual', 'tareas': ['respaldos', 'monitoreo'], 'descripcion': '',
        })
        self.assertEqual(Solicitud.objects.get().detalles['Frecuencia'], 'Mensual')

    def test_relacionar_con_solicitud_propia_y_no_ajena(self):
        propia = nueva_solicitud(self.cliente, tipo=Servicio.TIPO_CREACION, titulo='Sitio original')
        ajena = nueva_solicitud(crear_cliente('otro@correo.cl'))
        base = {'titulo': 'Error', 'url_sitio': 'https://miempresa.cl', 'tipo_problema': 'errores', 'prioridad': 'media', 'descripcion': 'Falla.'}
        respuesta = self.client.post(reverse('solicitar_soporte'), {**base, 'relacionada': ajena.pk})
        self.assertEqual(respuesta.status_code, 200)
        self.client.post(reverse('solicitar_soporte'), {**base, 'relacionada': propia.pk})
        nueva = Solicitud.objects.get(titulo='Error')
        self.assertEqual(nueva.relacionada, propia)
        self.assertContains(self.client.get(propia.get_absolute_url()), nueva.numero)

    def test_token_repetido_no_duplica(self):
        token = str(uuid.uuid4())
        datos = {'titulo': 'Error', 'url_sitio': 'https://miempresa.cl', 'tipo_problema': 'errores', 'prioridad': 'media', 'descripcion': 'Falla.', 'token_envio': token}
        self.client.post(reverse('solicitar_soporte'), datos)
        self.client.post(reverse('solicitar_soporte'), datos)
        self.assertEqual(Solicitud.objects.count(), 1)

    def test_formulario_invalido_no_crea_solicitud(self):
        self.client.post(reverse('solicitar_mejora'), {'titulo': '', 'url_sitio': 'no es url', 'descripcion': ''})
        self.assertFalse(Solicitud.objects.exists())


# Mensajes, archivos y respuesta a cotizaciones (CU11, CU12, CU13).
@override_settings(MEDIA_ROOT=MEDIA_PRUEBAS)
class ColaboracionTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.cliente = crear_cliente()
        self.staff = crear_staff()
        self.responsable = crear_staff('soporte@axztra.cl', superusuario=False, nombre='Franco')
        self.solicitud = nueva_solicitud(self.cliente, responsable=self.responsable)

    def test_mensaje_del_cliente_llega_al_responsable(self):
        self.client.force_login(self.cliente)
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post(reverse('enviar_mensaje', args=[self.solicitud.pk]), {'texto': 'Adjunto más información.'})
        self.assertRedirects(respuesta, f'{self.solicitud.get_absolute_url()}#mensajes', fetch_redirect_response=False)
        mensaje = MensajeSolicitud.objects.get()
        self.assertFalse(mensaje.es_equipo)
        self.assertEqual(mail.outbox[-1].to, ['soporte@axztra.cl'])

    def test_mensaje_del_equipo_queda_sin_leer_hasta_que_el_cliente_lo_ve(self):
        verificar_sesion(self.client, self.responsable)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('panel_solicitud', args=[self.solicitud.pk]), {'accion': 'mensaje', 'texto': 'Ya lo estamos revisando.'})
        self.assertEqual(mail.outbox[-1].to, ['cliente@correo.cl'])
        cliente = self.client_class()
        cliente.force_login(self.cliente)
        self.assertContains(cliente.get(reverse('mis_solicitudes')), '1 mensaje nuevo')
        cliente.get(self.solicitud.get_absolute_url())
        self.assertFalse(MensajeSolicitud.objects.filter(leido=False).exists())

    def test_cliente_no_escribe_en_solicitud_ajena(self):
        self.client.force_login(crear_cliente('otro@correo.cl'))
        respuesta = self.client.post(reverse('enviar_mensaje', args=[self.solicitud.pk]), {'texto': 'Hola'})
        self.assertEqual(respuesta.status_code, 404)

    def test_descarga_de_adjuntos_con_permisos(self):
        self.client.force_login(self.cliente)
        archivo = SimpleUploadedFile('logo.png', b'\x89PNG\r\n', content_type='image/png')
        self.client.post(reverse('subir_adjunto', args=[self.solicitud.pk]), {'archivo': archivo})
        adjunto = Adjunto.objects.get()
        url = reverse('descargar_adjunto', args=[adjunto.pk])
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('attachment', respuesta['Content-Disposition'])
        respuesta.close()
        otro = self.client_class()
        otro.force_login(crear_cliente('otro@correo.cl'))
        self.assertEqual(otro.get(url).status_code, 404)
        equipo = self.client_class()
        equipo.force_login(self.staff)
        respuesta = equipo.get(url)
        self.assertEqual(respuesta.status_code, 200)
        respuesta.close()

    def test_limite_de_mensajes(self):
        self.client.force_login(self.cliente)
        for _ in range(31):
            respuesta = self.client.post(reverse('enviar_mensaje', args=[self.solicitud.pk]), {'texto': 'Hola'})
        self.assertEqual(respuesta.status_code, 429)
        self.assertEqual(MensajeSolicitud.objects.count(), 30)


# Panel del equipo: estados, cotizaciones, tablero, permisos y exportaciones (CU15 a CU20, DA-03).
class PanelTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.cliente = crear_cliente()
        self.staff = crear_staff()
        verificar_sesion(self.client, self.staff)
        self.solicitud = nueva_solicitud(self.cliente, tipo=Servicio.TIPO_CREACION, titulo='Sitio corporativo')

    def _cotizar(self, items, plazo=20, validez=15):
        datos = {
            'accion': 'cotizacion', 'plazo_dias': plazo, 'validez_dias': validez, 'detalle': 'Incluye diseño y publicación.',
            'items-TOTAL_FORMS': str(len(items)), 'items-INITIAL_FORMS': '0', 'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
        }
        for i, (descripcion, cantidad, precio) in enumerate(items):
            datos.update({f'items-{i}-descripcion': descripcion, f'items-{i}-cantidad': cantidad, f'items-{i}-precio_unitario': precio})
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse('panel_solicitud', args=[self.solicitud.pk]), datos)

    def test_paginas_del_panel(self):
        for nombre in ['panel_inicio', 'panel_solicitudes', 'panel_tablero', 'panel_servicios', 'panel_contenido', 'panel_clientes', 'panel_consultas', 'panel_actividad']:
            with self.subTest(pagina=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)
        self.assertEqual(self.client.get(reverse('panel_solicitud', args=[self.solicitud.pk])).status_code, 200)

    def test_listado_con_consultas_acotadas(self):
        for i in range(15):
            nueva_solicitud(self.cliente, titulo=f'Solicitud {i}', responsable=self.staff)
        self.client.get(reverse('panel_solicitudes'))
        with CaptureQueriesContext(connection) as consultas:
            self.client.get(reverse('panel_solicitudes'))
        self.assertLessEqual(len(consultas), 8)

    def test_cotizacion_por_items_con_iva_y_versiones(self):
        respuesta = self._cotizar([('Diseño y desarrollo', 1, 500000), ('Páginas adicionales', 2, 30000)])
        self.assertRedirects(respuesta, reverse('panel_solicitud', args=[self.solicitud.pk]))
        cotizacion = Cotizacion.objects.get()
        self.assertEqual(cotizacion.monto, 560000)
        self.assertEqual(cotizacion.monto_iva, 106400)
        self.assertEqual(cotizacion.total, 666400)
        self.assertEqual(len(cotizacion.items), 2)
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado.codigo, EstadoSolicitud.COTIZADA)
        self.assertIn('$666.400', mail.outbox[-1].body)
        self._cotizar([('Diseño y desarrollo', 1, 450000)])
        cotizacion.refresh_from_db()
        self.assertEqual((cotizacion.version, cotizacion.monto), (2, 450000))

    def test_cotizacion_sin_items_validos(self):
        respuesta = self._cotizar([('Algo', 1, 500)])
        self.assertContains(respuesta, 'al menos $1.000')
        self.assertFalse(Cotizacion.objects.exists())

    def test_cliente_acepta_y_ve_el_documento(self):
        self._cotizar([('Sitio web', 1, 800000)])
        cliente = self.client_class()
        cliente.force_login(self.cliente)
        self.assertContains(cliente.get(self.solicitud.get_absolute_url()), 'Tu cotización está lista')
        documento = cliente.get(reverse('cotizacion_documento', args=[self.solicitud.pk]))
        self.assertContains(documento, '$952.000')
        cliente.post(reverse('responder_cotizacion', args=[self.solicitud.pk]), {'respuesta': 'aceptada', 'comentario': 'Adelante'})
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado.codigo, EstadoSolicitud.APROBADA)
        self.assertEqual(self.solicitud.cotizacion.respuesta_cliente, 'aceptada')

    def test_cotizacion_vencida_no_se_puede_aceptar(self):
        self._cotizar([('Sitio web', 1, 800000)])
        Cotizacion.objects.update(fecha_emision=timezone.now() - timedelta(days=30))
        cliente = self.client_class()
        cliente.force_login(self.cliente)
        cliente.post(reverse('responder_cotizacion', args=[self.solicitud.pk]), {'respuesta': 'aceptada'})
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado.codigo, EstadoSolicitud.COTIZADA)

    def test_cambio_de_estado_registra_historial_auditoria_y_primera_respuesta(self):
        en_revision = EstadoSolicitud.obtener(EstadoSolicitud.EN_REVISION)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('panel_solicitud', args=[self.solicitud.pk]), {
                'accion': 'estado', 'estado': en_revision.pk, 'comentario': 'Revisando', 'notificar': 'on',
            })
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, en_revision)
        self.assertIsNotNone(self.solicitud.fecha_primera_respuesta)
        self.assertTrue(RegistroActividad.objects.filter(accion='estado', solicitud=self.solicitud).exists())
        self.assertEqual(mail.outbox[-1].to, ['cliente@correo.cl'])

    def test_no_se_marca_cotizada_sin_cotizacion(self):
        cotizada = EstadoSolicitud.obtener(EstadoSolicitud.COTIZADA)
        respuesta = self.client.post(reverse('panel_solicitud', args=[self.solicitud.pk]), {'accion': 'estado', 'estado': cotizada.pk})
        self.assertContains(respuesta, 'Primero emite la cotización definitiva')

    def test_tablero_mueve_solicitudes(self):
        url = reverse('panel_mover_solicitud', args=[self.solicitud.pk])
        respuesta = self.client.post(url, json.dumps({'estado': 'en_revision'}), content_type='application/json')
        self.assertEqual(respuesta.json()['estado'], 'en_revision')
        respuesta = self.client.post(url, json.dumps({'estado': 'cotizada'}), content_type='application/json')
        self.assertEqual(respuesta.status_code, 400)
        respuesta = self.client.post(url, json.dumps({'estado': 'inexistente'}), content_type='application/json')
        self.assertEqual(respuesta.status_code, 400)

    def test_asignar_responsable_avisa_y_audita(self):
        franco = crear_staff('soporte@axztra.cl', superusuario=False, nombre='Franco')
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('panel_solicitud', args=[self.solicitud.pk]), {
                'accion': 'gestion', 'responsable': franco.pk, 'prioridad': 'alta', 'notas_internas': 'Cliente importante',
            })
        self.solicitud.refresh_from_db()
        self.assertEqual((self.solicitud.responsable, self.solicitud.prioridad), (franco, 'alta'))
        self.assertEqual(mail.outbox[-1].to, ['soporte@axztra.cl'])
        self.assertTrue(RegistroActividad.objects.filter(accion='asignacion').exists())
        self.assertContains(self.client.get(reverse('panel_solicitudes'), {'responsable': franco.pk}), self.solicitud.numero)

    def test_solicitudes_fuera_de_plazo(self):
        atrasada = nueva_solicitud(self.cliente, titulo='Urgente', prioridad='urgente')
        Solicitud.objects.filter(pk=atrasada.pk).update(fecha_solicitud=timezone.now() - timedelta(hours=5))
        atrasada.refresh_from_db()
        self.assertTrue(atrasada.atrasada)
        self.assertEqual(list(Solicitud.objects.filter(Solicitud.filtro_atrasadas())), [atrasada])
        respuesta = self.client.get(reverse('panel_solicitudes'), {'atrasadas': '1'})
        self.assertContains(respuesta, atrasada.numero)
        self.assertNotContains(respuesta, self.solicitud.numero)

    def test_exportaciones_csv(self):
        respuesta = self.client.get(reverse('panel_solicitudes'), {'exportar': 'csv'})
        contenido = b''.join(respuesta.streaming_content).decode('utf-8')
        self.assertTrue(contenido.startswith('\ufeffNúmero;Título'))
        self.assertIn(self.solicitud.numero, contenido)
        respuesta = self.client.get(reverse('panel_clientes'), {'exportar': 'csv'})
        self.assertIn('cliente@correo.cl', b''.join(respuesta.streaming_content).decode('utf-8'))
        self.assertEqual(RegistroActividad.objects.filter(accion='exportacion').count(), 2)

    def test_permisos_por_rol(self):
        soporte = crear_staff('soporte@axztra.cl', superusuario=False)
        equipo = self.client_class()
        verificar_sesion(equipo, soporte)
        self.assertEqual(equipo.get(reverse('panel_solicitudes')).status_code, 200)
        for nombre in ['panel_servicios', 'panel_contenido', 'panel_actividad']:
            with self.subTest(pagina=nombre):
                self.assertEqual(equipo.get(reverse(nombre)).status_code, 403)
        soporte.user_permissions.add(Permission.objects.get(codename='change_servicio'))
        equipo = self.client_class()
        verificar_sesion(equipo, User.objects.get(pk=soporte.pk))
        self.assertEqual(equipo.get(reverse('panel_servicios')).status_code, 200)

    def test_crud_de_servicios_y_contenido(self):
        categoria = Servicio.objects.first().categoria
        respuesta = self.client.post(reverse('panel_servicio_nuevo'), {
            'nombre': 'Auditoría de accesibilidad', 'tipo': 'Mejora', 'categoria': categoria.pk,
            'resumen': 'Revisión de accesibilidad.', 'descripcion': 'Informe completo.', 'incluye': 'Informe\nCorrecciones',
            'precio_base': 90000, 'plazo_referencial': '1 semana', 'activo': 'on',
        })
        self.assertRedirects(respuesta, reverse('panel_servicios'))
        servicio = Servicio.objects.get(nombre='Auditoría de accesibilidad')
        self.assertContains(self.client.get(reverse('catalogo')), 'Auditoría de accesibilidad')
        self.client.post(reverse('panel_servicio_estado', args=[servicio.pk]))
        self.assertNotContains(self.client.get(reverse('catalogo')), servicio.get_absolute_url())
        self.client.post(reverse('panel_pregunta_nueva'), {
            'pregunta': '¿Trabajan con municipalidades?', 'respuesta': 'Sí, trabajamos con organismos públicos.',
            'palabras_clave': 'municipalidad, municipio', 'orden': 20, 'activa': 'on',
        })
        self.assertContains(self.client.get(reverse('inicio')), 'Trabajan con municipalidades')
        self.client.post(reverse('panel_contenido'), {
            'correo_contacto': 'hola@axztra.cl', 'whatsapp': '+56 9 8765 4321', 'whatsapp_visible': '+56 9 8765 4321',
            'ubicacion': 'Concepción', 'horario': 'Lunes a viernes', 'aviso': 'Atención especial en fiestas patrias',
        })
        self.assertEqual(ConfiguracionSitio.actual().whatsapp, '56987654321')
        self.assertContains(self.client.get(reverse('inicio')), 'Atención especial en fiestas patrias')

    def test_solicitud_cerrada_no_se_cotiza(self):
        self.solicitud.estado = EstadoSolicitud.obtener(EstadoSolicitud.CANCELADA)
        self.solicitud.save()
        self._cotizar([('Sitio web', 1, 800000)])
        self.assertFalse(Cotizacion.objects.exists())


# API REST con tokens (CU22, RF12).
class APITests(BaseTest):
    def setUp(self):
        super().setUp()
        self.cliente = crear_cliente()
        self.solicitud = nueva_solicitud(self.cliente)
        registrar_historial(self.solicitud, None, 'Solicitud registrada por el cliente.', self.cliente)
        self.token, self.valor = TokenAPI.generar('Facturación')

    def test_servicios_publicos(self):
        datos = self.client.get(reverse('api_servicios')).json()
        self.assertTrue(any(s['slug'] == 'landing-page' for s in datos['resultados']))

    def test_estimaciones(self):
        respuesta = self.client.post(reverse('api_estimaciones'), json.dumps({
            'tipo_sitio': 'corporativo', 'complejidad': 'media', 'num_paginas': 7,
            'funcionalidades': ['formulario', 'galeria'], 'integraciones': ['whatsapp', 'mapa'],
        }), content_type='application/json')
        self.assertEqual(respuesta.json()['total'], 531250)
        respuesta = self.client.post(reverse('api_estimaciones'), json.dumps({'funcionalidades': ['volar']}), content_type='application/json')
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(self.client.post(reverse('api_estimaciones'), 'no es json', content_type='application/json').status_code, 400)

    def test_solicitudes_requieren_token(self):
        self.assertEqual(self.client.get(reverse('api_solicitudes')).status_code, 401)
        self.assertEqual(self.client.get(reverse('api_solicitudes'), HTTP_AUTHORIZATION='Token axz_falso').status_code, 401)

    def test_solicitudes_con_token(self):
        cabecera = {'HTTP_AUTHORIZATION': f'Token {self.valor}'}
        datos = self.client.get(reverse('api_solicitudes'), {'por_pagina': 10}, **cabecera).json()
        self.assertEqual(datos['total'], 1)
        self.assertEqual(datos['resultados'][0]['numero'], self.solicitud.numero)
        detalle = self.client.get(reverse('api_solicitud', args=[self.solicitud.numero]), **cabecera).json()
        self.assertEqual(detalle['historial'][0]['estado'], 'Recibida')
        self.assertEqual(self.client.get(reverse('api_solicitud', args=['AXZ-0000-0000']), **cabecera).status_code, 404)
        self.token.refresh_from_db()
        self.assertIsNotNone(self.token.ultimo_uso)
        self.token.activo = False
        self.token.save()
        self.assertEqual(self.client.get(reverse('api_solicitudes'), **cabecera).status_code, 401)

    def test_limite_de_peticiones(self):
        cuerpo = json.dumps({'tipo_sitio': 'landing'})
        for _ in range(61):
            respuesta = self.client.post(reverse('api_estimaciones'), cuerpo, content_type='application/json')
        self.assertEqual(respuesta.status_code, 429)


# Asistente virtual y sugerencias por rubro (CU03, RF11).
class AsistenteTests(BaseTest):
    def test_intenciones_principales(self):
        casos = {
            'hola': 'saludo',
            '¿cuánto cuesta una página web?': 'estimacion',
            'cuanto cuesta la tienda online': 'servicio',
            'tengo una pastelería, qué le pondrías': 'ideas',
            'mi sitio está caído': 'soporte',
            '¿cuánto se demoran?': 'plazos',
            '¿aceptan tarjeta?': 'pagos',
            '¿hacen apps para celular?': 'aplicacion',
            'xyzzy': 'no_entendido',
        }
        for texto, intencion in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(AsistenteVirtual().responder(texto)['intencion'], intencion)

    def test_estado_de_solicitud_solo_para_su_duenio(self):
        cliente = crear_cliente()
        solicitud = nueva_solicitud(cliente)
        respuesta = AsistenteVirtual(cliente).responder(f'¿Cómo va la {solicitud.numero}?')
        self.assertIn('Recibida', respuesta['respuesta'])
        otro = AsistenteVirtual(crear_cliente('otro@correo.cl')).responder(f'¿Cómo va la {solicitud.numero}?')
        self.assertNotIn(solicitud.titulo, otro['respuesta'])

    def test_usa_preguntas_frecuentes(self):
        PreguntaFrecuente.objects.create(pregunta='¿Trabajan con municipalidades?', respuesta='Sí, con organismos públicos.', palabras_clave='municipalidad, municipio, municipal')
        self.assertIn('organismos públicos', AsistenteVirtual().responder('trabajan con alguna municipalidad o municipio')['respuesta'])

    def test_endpoint_guarda_conversacion_de_visitante(self):
        respuesta = self.client.post(reverse('asistente_mensaje'), json.dumps({'mensaje': 'hola'}), content_type='application/json')
        self.assertEqual(respuesta.json()['intencion'], 'saludo')
        self.assertEqual(MensajeAsistente.objects.count(), 2)
        historial = self.client.get(reverse('asistente_historial')).json()
        self.assertEqual(len(historial['mensajes']), 2)

    def test_endpoint_valida_entrada(self):
        self.assertEqual(self.client.post(reverse('asistente_mensaje'), 'x', content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post(reverse('asistente_mensaje'), json.dumps({'mensaje': '  '}), content_type='application/json').status_code, 400)

    def test_historial_separado_por_usuario(self):
        self.client.force_login(crear_cliente())
        self.client.post(reverse('asistente_mensaje'), json.dumps({'mensaje': 'hola'}), content_type='application/json')
        otro = self.client_class()
        otro.force_login(crear_cliente('otro@correo.cl'))
        self.assertEqual(otro.get(reverse('asistente_historial')).json()['mensajes'], [])

    def test_sugerencias_para_el_formulario(self):
        self.assertEqual(self.client.post(reverse('asistente_sugerencias'), '{}', content_type='application/json').status_code, 302)
        self.client.force_login(crear_cliente())
        respuesta = self.client.post(reverse('asistente_sugerencias'), json.dumps({
            'descripcion': 'Restaurante con delivery y reservas de mesa', 'rubro': 'gastronomia', 'objetivos': ['reservas'],
        }), content_type='application/json')
        claves = [f['clave'] for f in respuesta.json()['funcionalidades']]
        self.assertIn('reservas', claves)


# Métodos de los modelos.
class ModeloTests(BaseTest):
    def test_numero_correlativo_unico(self):
        cliente = crear_cliente()
        a, b = nueva_solicitud(cliente), nueva_solicitud(cliente)
        self.assertRegex(a.numero, r'^AXZ-\d{4}-\d{4}$')
        self.assertNotEqual(a.numero, b.numero)

    def test_pasos_de_seguimiento(self):
        solicitud = nueva_solicitud(crear_cliente())
        solicitud.estado = EstadoSolicitud.obtener(EstadoSolicitud.COTIZADA)
        pasos = solicitud.pasos_seguimiento
        self.assertEqual([p['situacion'] for p in pasos[:4]], ['hecho', 'hecho', 'actual', 'pendiente'])

    def test_datos_iniciales(self):
        self.assertEqual(EstadoSolicitud.objects.count(), 8)
        self.assertGreaterEqual(Servicio.objects.count(), 10)
        self.assertGreaterEqual(PreguntaFrecuente.objects.count(), 9)
        self.assertEqual(ConfiguracionSitio.actual().pk, 1)

    def test_configuracion_es_unica(self):
        ConfiguracionSitio(correo_contacto='otro@axztra.cl').save()
        self.assertEqual(ConfiguracionSitio.objects.count(), 1)
        self.assertEqual(ConfiguracionSitio.actual().correo_contacto, 'otro@axztra.cl')


# Restricciones de la base de datos (RNF03).
@override_settings(MEDIA_ROOT=MEDIA_PRUEBAS)
class IntegridadBaseDatosTests(BaseTest):
    def test_la_base_rechaza_datos_invalidos(self):
        cliente = crear_cliente()
        solicitud = nueva_solicitud(cliente)
        casos = {
            'plazo de cotización en cero': lambda: Cotizacion.objects.create(solicitud=solicitud, monto=1000, plazo_dias=0, detalle='Alcance'),
            'rango de estimación invertido': lambda: Estimacion.objects.create(solicitud=solicitud, total=10, monto_minimo=20, monto_maximo=10),
            'prioridad inexistente': lambda: Solicitud.objects.filter(pk=solicitud.pk).update(prioridad='altisima'),
            'mensaje vacío': lambda: MensajeSolicitud.objects.create(solicitud=solicitud, texto=''),
            'servicio duplicado': lambda: Servicio.objects.create(nombre='LANDING PAGE', slug='landing-duplicada', tipo='Creacion', resumen='x', descripcion='x'),
            'páginas fuera de rango': lambda: RequerimientoWeb.objects.create(nombre_negocio='x', rubro='otro', descripcion_negocio='x', tipo_sitio='tienda', num_paginas=0),
        }
        for nombre, caso in casos.items():
            with self.subTest(caso=nombre):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        caso()

    def test_correo_unico_sin_distinguir_mayusculas(self):
        crear_cliente('ana@correo.cl')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(username='otra-cuenta', email='ANA@correo.cl', password='ClaveSegura2026')
        User.objects.create_user(username='sin-correo-1', email='', password='ClaveSegura2026')
        User.objects.create_user(username='sin-correo-2', email='', password='ClaveSegura2026')

    def test_no_se_pierden_solicitudes_al_borrar_un_cliente(self):
        cliente = crear_cliente()
        nueva_solicitud(cliente)
        with self.assertRaises(ProtectedError):
            cliente.delete()

    def test_borrar_un_adjunto_elimina_el_archivo(self):
        cliente = crear_cliente()
        solicitud = nueva_solicitud(cliente)
        adjunto = guardar_adjunto(solicitud, SimpleUploadedFile('plano.pdf', b'%PDF-1.4', content_type='application/pdf'), cliente)
        ruta = adjunto.archivo.path
        self.assertTrue(os.path.exists(ruta))
        with self.captureOnCommitCallbacks(execute=True):
            adjunto.delete()
        self.assertFalse(os.path.exists(ruta))


# Comandos de manage.py.
class ComandosTests(BaseTest):
    def test_comprobar_base_confirma_la_conexion(self):
        salida = StringIO()
        call_command('comprobar_base', stdout=salida)
        self.assertIn('Conexión correcta', salida.getvalue())

    def test_datos_demo_es_repetible(self):
        salida = StringIO()
        call_command('datos_demo', stdout=salida)
        call_command('datos_demo', stdout=salida)
        self.assertIn('cliente@axztra.cl / Cliente2026', salida.getvalue())
        self.assertEqual(Solicitud.objects.count(), 9)
        self.assertTrue(Solicitud.objects.filter(Solicitud.filtro_atrasadas()).exists())
        self.assertTrue(Cotizacion.objects.filter(respuesta_cliente='aceptada').exists())
        self.assertEqual(User.objects.get(email='admin@axztra.cl').is_superuser, True)
        self.assertEqual(len(mail.outbox), 0)

    def test_generar_carga(self):
        call_command('generar_carga', clientes=5, solicitudes=40, stdout=StringIO())
        self.assertEqual(Solicitud.objects.count(), 40)
        self.assertEqual(Solicitud.objects.filter(numero__startswith='AXZ-').count(), 40)
        self.assertEqual(HistorialSolicitud.objects.count(), 40)
        self.assertEqual(Estimacion.objects.count(), Solicitud.objects.filter(tipo=Servicio.TIPO_CREACION).count())

    def test_crear_token_y_limpiar(self):
        salida = StringIO()
        call_command('crear_token_api', 'ERP', stdout=salida)
        valor = re.search(r'(axz_\S+)', salida.getvalue()).group(1)
        self.assertEqual(self.client.get(reverse('api_solicitudes'), HTTP_AUTHORIZATION=f'Token {valor}').status_code, 200)
        usuario = crear_cliente()
        CodigoVerificacion.objects.create(usuario=usuario, codigo_hash='x', expira=timezone.now() - timedelta(days=3))
        salida = StringIO()
        call_command('limpiar_datos', stdout=salida)
        self.assertIn('Códigos de verificación eliminados: 1', salida.getvalue())


def tearDownModule():
    shutil.rmtree(MEDIA_PRUEBAS, ignore_errors=True)
