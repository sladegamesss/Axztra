import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .asistente import AsistenteVirtual
from .estimacion import calcular_estimacion
from .forms import validar_rut
from .models import (
    CodigoVerificacion,
    Cotizacion,
    EstadoSolicitud,
    Estimacion,
    HistorialSolicitud,
    MensajeAsistente,
    PerfilCliente,
    Servicio,
    Solicitud,
)
from .verificacion import CLAVE_SESION_VERIFICADA

User = get_user_model()

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


def crear_cliente(email='cliente@correo.cl', password='ClaveSegura2026'):
    usuario = User.objects.create_user(username=email, email=email, password=password, first_name='Ana', last_name='Rojas')
    PerfilCliente.objects.create(usuario=usuario)
    return usuario


def crear_staff(email='admin@axztra.cl', password='ClaveAdmin2026'):
    return User.objects.create_user(username=email, email=email, password=password, first_name='Camilo', is_staff=True, is_superuser=True)


def codigo_desde_correo():
    for mensaje in reversed(mail.outbox):
        encontrado = re.search(r'^\s+(\d{6})\s*$', mensaje.body, re.MULTILINE)
        if encontrado:
            return encontrado.group(1)
    raise AssertionError('No se encontró un código en los correos enviados.')


class EstimacionTests(TestCase):
    def test_formula_con_factor_de_complejidad(self):
        r = calcular_estimacion('corporativo', 'media', 7, ['formulario', 'galeria'], ['whatsapp'])
        esperado = 300000 + int(2 * 30000 * 1.25) + int(40000 * 1.25) + int(50000 * 1.25) + int(15000 * 1.25)
        self.assertEqual(r['total'], esperado)
        self.assertLessEqual(r['monto_minimo'], r['total'])
        self.assertGreaterEqual(r['monto_maximo'], r['total'])
        self.assertEqual((r['semanas_minimas'], r['semanas_maximas']), (3, 5))

    def test_complejidad_basica_sin_extras(self):
        r = calcular_estimacion('landing', 'basica', 1, [], [])
        self.assertEqual(r['total'], 220000)
        self.assertEqual(len(r['desglose']), 1)

    def test_tienda_suma_semana_y_claves_invalidas_se_ignoran(self):
        r = calcular_estimacion('tienda', 'alta', 5, ['tienda', 'inexistente'], ['pagos'])
        self.assertEqual(r['semanas_minimas'], 6)
        self.assertEqual(len(r['desglose']), 3)


class RutTests(TestCase):
    def test_rut_valido_se_formatea(self):
        self.assertEqual(validar_rut('11111111-1'), '11.111.111-1')
        self.assertEqual(validar_rut(''), '')

    def test_rut_invalido(self):
        from django import forms
        with self.assertRaises(forms.ValidationError):
            validar_rut('12345678-0')


class PaginasPublicasTests(TestCase):
    def test_paginas_publicas_responden(self):
        for nombre in ['inicio', 'catalogo', 'registro', 'login', 'recuperar_clave']:
            respuesta = self.client.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, 200, nombre)

    def test_detalle_de_servicio(self):
        servicio = Servicio.objects.get(slug='tienda-online')
        respuesta = self.client.get(servicio.get_absolute_url())
        self.assertContains(respuesta, 'Tienda online')

    def test_servicio_inactivo_no_se_muestra(self):
        servicio = Servicio.objects.get(slug='tienda-online')
        servicio.activo = False
        servicio.save()
        self.assertEqual(self.client.get(servicio.get_absolute_url()).status_code, 404)
        self.assertNotContains(self.client.get(reverse('catalogo')), 'Tienda online')

    def test_filtros_del_catalogo(self):
        respuesta = self.client.get(reverse('catalogo'), {'tipo': 'Soporte'})
        self.assertEqual(len(respuesta.context['servicios']), Servicio.objects.filter(tipo='Soporte', activo=True).count())
        respuesta = self.client.get(reverse('catalogo'), {'q': 'velocidad'})
        self.assertEqual(len(respuesta.context['servicios']), 1)

    def test_pagina_404_personalizada(self):
        respuesta = self.client.get('/no-existe/')
        self.assertEqual(respuesta.status_code, 404)

    def test_rutas_privadas_piden_sesion(self):
        for nombre in ['mis_solicitudes', 'nueva_solicitud', 'crear_web', 'mi_cuenta']:
            respuesta = self.client.get(reverse(nombre))
            self.assertRedirects(respuesta, f"{reverse('login')}?next={reverse(nombre)}")


class CuentasTests(TestCase):
    def test_registro_crea_usuario_perfil_e_inicia_sesion(self):
        respuesta = self.client.post(reverse('registro'), {
            'first_name': 'Pedro', 'last_name': 'Soto', 'email': 'Pedro@Correo.cl',
            'empresa': 'Soto Ltda', 'telefono': '+56 9 8765 4321',
            'password1': 'ClaveMuySegura2026', 'password2': 'ClaveMuySegura2026', 'acepta_terminos': 'on',
        })
        self.assertRedirects(respuesta, reverse('nueva_solicitud'))
        usuario = User.objects.get(email='pedro@correo.cl')
        self.assertEqual(usuario.perfil_cliente.empresa, 'Soto Ltda')
        self.assertEqual(len(mail.outbox), 1)

    def test_registro_rechaza_correo_duplicado(self):
        crear_cliente('ana@correo.cl')
        respuesta = self.client.post(reverse('registro'), {
            'first_name': 'Ana', 'last_name': 'Otra', 'email': 'ANA@correo.cl',
            'password1': 'ClaveMuySegura2026', 'password2': 'ClaveMuySegura2026', 'acepta_terminos': 'on',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(User.objects.filter(email__iexact='ana@correo.cl').count(), 1)

    def test_login_con_correo(self):
        crear_cliente()
        respuesta = self.client.post(reverse('login'), {'email': 'CLIENTE@correo.cl', 'password': 'ClaveSegura2026'})
        self.assertRedirects(respuesta, reverse('inicio'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_login_incorrecto(self):
        crear_cliente()
        respuesta = self.client.post(reverse('login'), {'email': 'cliente@correo.cl', 'password': 'otra'})
        self.assertContains(respuesta, 'no son correctos')

    def test_login_respeta_next_seguro(self):
        crear_cliente()
        respuesta = self.client.post(reverse('login'), {'email': 'cliente@correo.cl', 'password': 'ClaveSegura2026', 'next': 'https://sitio-malicioso.com/'})
        self.assertRedirects(respuesta, reverse('inicio'))

    def test_logout_por_post(self):
        crear_cliente()
        self.client.login(username='cliente@correo.cl', password='ClaveSegura2026')
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.client.post(reverse('logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_actualizar_mis_datos(self):
        usuario = crear_cliente()
        self.client.force_login(usuario)
        respuesta = self.client.post(reverse('mi_cuenta'), {
            'first_name': 'Ana María', 'last_name': 'Rojas', 'empresa': 'Mi pyme', 'rut': '11111111-1',
            'telefono': '+56912345678', 'ciudad': 'Hualpén', 'recibir_notificaciones': 'on',
        })
        self.assertRedirects(respuesta, reverse('mi_cuenta'))
        usuario.refresh_from_db()
        self.assertEqual(usuario.first_name, 'Ana María')
        self.assertEqual(usuario.perfil_cliente.rut, '11.111.111-1')

    def test_recuperar_contrasena_envia_correo(self):
        crear_cliente()
        respuesta = self.client.post(reverse('recuperar_clave'), {'email': 'cliente@correo.cl'})
        self.assertRedirects(respuesta, reverse('recuperar_enviado'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/cuenta/recuperar/', mail.outbox[0].body)


class DosFactoresTests(TestCase):
    def setUp(self):
        self.staff = crear_staff()

    def test_staff_requiere_codigo_y_luego_accede_al_panel(self):
        respuesta = self.client.post(reverse('login'), {'email': 'admin@axztra.cl', 'password': 'ClaveAdmin2026', 'next': reverse('panel_inicio')})
        self.assertRedirects(respuesta, reverse('verificar_codigo'))
        self.assertNotIn('_auth_user_id', self.client.session)
        codigo = codigo_desde_correo()
        respuesta = self.client.post(reverse('verificar_codigo'), {'codigo': codigo})
        self.assertRedirects(respuesta, reverse('panel_inicio'))
        self.assertEqual(self.client.get(reverse('panel_inicio')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)

    def test_codigo_incorrecto_y_limite_de_intentos(self):
        self.client.post(reverse('login'), {'email': 'admin@axztra.cl', 'password': 'ClaveAdmin2026'})
        correcto = codigo_desde_correo()
        incorrecto = '000000' if correcto != '000000' else '111111'
        for _ in range(5):
            respuesta = self.client.post(reverse('verificar_codigo'), {'codigo': incorrecto})
            self.assertEqual(respuesta.status_code, 200)
        respuesta = self.client.post(reverse('verificar_codigo'), {'codigo': correcto})
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_codigo_expirado(self):
        self.client.post(reverse('login'), {'email': 'admin@axztra.cl', 'password': 'ClaveAdmin2026'})
        codigo = codigo_desde_correo()
        CodigoVerificacion.objects.update(expira=timezone.now() - timedelta(minutes=1))
        respuesta = self.client.post(reverse('verificar_codigo'), {'codigo': codigo})
        self.assertContains(respuesta, 'expiró')

    def test_sesion_sin_verificar_no_entra_al_panel_ni_al_admin(self):
        self.client.force_login(self.staff)
        respuesta = self.client.get(reverse('panel_inicio'))
        self.assertTrue(respuesta.url.startswith(reverse('verificar_codigo')))
        respuesta = self.client.get(reverse('admin:index'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.url.startswith(reverse('admin:login')))

    def test_usuario_autenticado_sin_verificar_recibe_codigo_al_entrar(self):
        self.client.force_login(self.staff)
        self.client.get(reverse('verificar_codigo'))
        codigo = codigo_desde_correo()
        respuesta = self.client.post(reverse('verificar_codigo'), {'codigo': codigo})
        self.assertRedirects(respuesta, reverse('panel_inicio'))

    def test_reenviar_codigo_invalida_el_anterior(self):
        self.client.post(reverse('login'), {'email': 'admin@axztra.cl', 'password': 'ClaveAdmin2026'})
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


class SolicitudWebTests(TestCase):
    def setUp(self):
        self.cliente = crear_cliente()
        self.staff = crear_staff()
        self.client.force_login(self.cliente)

    def test_flujo_completo_formulario_estimacion_y_confirmacion(self):
        respuesta = self.client.get(reverse('crear_web'))
        self.assertEqual(respuesta.status_code, 200)
        respuesta = self.client.post(reverse('crear_web'), DATOS_WEB)
        self.assertRedirects(respuesta, reverse('estimacion_web'))
        respuesta = self.client.get(reverse('estimacion_web'))
        self.assertContains(respuesta, 'Tu estimación referencial')
        self.assertEqual(Solicitud.objects.count(), 0)

        respuesta = self.client.get(reverse('crear_web') + '?editar=1')
        self.assertContains(respuesta, 'Cafetería Aroma')

        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post(reverse('estimacion_web'))
        solicitud = Solicitud.objects.get()
        self.assertRedirects(respuesta, solicitud.get_absolute_url())
        self.assertRegex(solicitud.numero, r'^AXZ-\d{4}-\d{4}$')
        self.assertEqual(solicitud.estado.codigo, EstadoSolicitud.RECIBIDA)
        self.assertEqual(solicitud.requerimiento.funcionalidades, ['formulario', 'galeria'])
        self.assertEqual(Estimacion.objects.get(solicitud=solicitud).total, calcular_estimacion('corporativo', 'media', 7, ['formulario', 'galeria'], ['whatsapp', 'mapa'])['total'])
        self.assertEqual(HistorialSolicitud.objects.filter(solicitud=solicitud).count(), 1)
        destinatarios = {d for m in mail.outbox for d in m.to}
        self.assertIn('cliente@correo.cl', destinatarios)
        self.assertIn('admin@axztra.cl', destinatarios)
        self.assertNotIn('axztra_borrador_web', self.client.session)
        self.assertContains(self.client.get(solicitud.get_absolute_url()), solicitud.numero)

    def test_errores_de_validacion_vuelven_al_paso_correcto(self):
        datos = dict(DATOS_WEB, objetivos=[], nombre_negocio='')
        respuesta = self.client.post(reverse('crear_web'), datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['paso_inicial'], 2)

    def test_sitio_actual_requiere_url(self):
        datos = dict(DATOS_WEB, tiene_sitio_actual='si', url_sitio_actual='')
        respuesta = self.client.post(reverse('crear_web'), datos)
        self.assertEqual(respuesta.context['paso_inicial'], 1)

    def test_fecha_en_pasado_no_se_acepta(self):
        datos = dict(DATOS_WEB, fecha_deseada='2020-01-01')
        respuesta = self.client.post(reverse('crear_web'), datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('fecha_deseada', respuesta.context['form'].errors)

    def test_estimacion_sin_borrador_redirige(self):
        self.assertRedirects(self.client.get(reverse('estimacion_web')), reverse('crear_web'))

    def test_servicio_preseleccionado(self):
        servicio = Servicio.objects.get(slug='tienda-online')
        respuesta = self.client.get(servicio.url_solicitud)
        self.assertContains(respuesta, servicio.nombre)
        self.client.post(reverse('crear_web'), dict(DATOS_WEB, servicio=servicio.pk))
        self.client.post(reverse('estimacion_web'))
        self.assertEqual(Solicitud.objects.get().servicio, servicio)


class SolicitudesSimplesTests(TestCase):
    def setUp(self):
        self.cliente = crear_cliente()
        self.client.force_login(self.cliente)

    def test_mejora(self):
        respuesta = self.client.post(reverse('solicitar_mejora'), {
            'titulo': 'Rediseño', 'url_sitio': 'misitio.cl', 'tipos_mejora': ['rediseno', 'seo'], 'descripcion': 'Quiero modernizarlo.',
        })
        solicitud = Solicitud.objects.get()
        self.assertRedirects(respuesta, solicitud.get_absolute_url())
        self.assertEqual(solicitud.tipo, Servicio.TIPO_MEJORA)
        self.assertEqual(solicitud.url_sitio, 'https://misitio.cl')
        self.assertIn('Rediseño visual', solicitud.detalles['Mejoras solicitadas'])

    def test_soporte_con_prioridad(self):
        self.client.post(reverse('solicitar_soporte'), {
            'titulo': 'Sitio caído', 'url_sitio': 'https://misitio.cl', 'tipo_problema': 'caido', 'prioridad': 'urgente', 'descripcion': 'No carga.',
        })
        solicitud = Solicitud.objects.get()
        self.assertEqual(solicitud.prioridad, 'urgente')
        self.assertEqual(solicitud.detalles['Tipo de problema'], 'El sitio no carga o está caído')

    def test_mantenimiento(self):
        self.client.post(reverse('solicitar_mantenimiento'), {
            'titulo': 'Plan mensual', 'url_sitio': 'https://misitio.cl', 'plataforma': 'wordpress', 'frecuencia': 'mensual', 'tareas': ['respaldos'],
        })
        solicitud = Solicitud.objects.get()
        self.assertEqual(solicitud.tipo, Servicio.TIPO_MANTENIMIENTO)
        self.assertEqual(solicitud.descripcion, 'Sin información adicional.')

    def test_formulario_invalido_no_crea_solicitud(self):
        respuesta = self.client.post(reverse('solicitar_mejora'), {'titulo': '', 'url_sitio': 'no es url'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Solicitud.objects.count(), 0)

    def test_paginas_de_formularios(self):
        for nombre in ['nueva_solicitud', 'solicitar_mejora', 'solicitar_soporte', 'solicitar_mantenimiento', 'mis_solicitudes', 'mi_cuenta']:
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200, nombre)


class GestionYPermisosTests(TestCase):
    def setUp(self):
        self.cliente = crear_cliente()
        self.otro = crear_cliente('otro@correo.cl')
        self.staff = crear_staff()
        self.client.force_login(self.cliente)
        self.client.post(reverse('solicitar_soporte'), {
            'titulo': 'Error en formulario', 'url_sitio': 'https://misitio.cl', 'tipo_problema': 'errores', 'prioridad': 'media', 'descripcion': 'Falla.',
        })
        self.solicitud = Solicitud.objects.get()

    def entrar_como_staff(self):
        self.client.force_login(self.staff)
        sesion = self.client.session
        sesion[CLAVE_SESION_VERIFICADA] = self.staff.pk
        sesion.save()

    def test_otro_cliente_no_ve_la_solicitud(self):
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(self.solicitud.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.post(reverse('cancelar_solicitud', args=[self.solicitud.pk])).status_code, 404)

    def test_cambio_de_estado_registra_historial_y_notifica(self):
        self.entrar_como_staff()
        mail.outbox.clear()
        en_revision = EstadoSolicitud.obtener(EstadoSolicitud.EN_REVISION)
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post(reverse('panel_solicitud', args=[self.solicitud.pk]), {
                'accion': 'estado', 'estado': en_revision.pk, 'comentario': 'Revisando', 'notificar': 'on',
            })
        self.assertRedirects(respuesta, reverse('panel_solicitud', args=[self.solicitud.pk]))
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, en_revision)
        self.assertEqual(self.solicitud.historial.count(), 2)
        self.assertEqual(mail.outbox[-1].to, ['cliente@correo.cl'])

    def test_no_se_puede_marcar_cotizada_sin_cotizacion(self):
        self.entrar_como_staff()
        cotizada = EstadoSolicitud.obtener(EstadoSolicitud.COTIZADA)
        respuesta = self.client.post(reverse('panel_solicitud', args=[self.solicitud.pk]), {'accion': 'estado', 'estado': cotizada.pk})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Primero emite la cotización')

    def test_cotizacion_y_aceptacion_del_cliente(self):
        self.entrar_como_staff()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('panel_solicitud', args=[self.solicitud.pk]), {
                'accion': 'cotizacion', 'monto': '85000', 'plazo_dias': '3', 'validez_dias': '15', 'detalle': 'Corrección del formulario.',
            })
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado.codigo, EstadoSolicitud.COTIZADA)
        self.assertEqual(Cotizacion.objects.get().monto, 85000)
        self.assertIn('Cotización disponible', mail.outbox[-1].subject)

        self.client.force_login(self.cliente)
        self.assertContains(self.client.get(self.solicitud.get_absolute_url()), 'Aceptar cotización')
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('responder_cotizacion', args=[self.solicitud.pk]), {'respuesta': 'aceptada', 'comentario': 'Perfecto'})
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado.codigo, EstadoSolicitud.APROBADA)
        self.assertEqual(self.solicitud.cotizacion.respuesta_cliente, 'aceptada')
        respuesta = self.client.post(reverse('responder_cotizacion', args=[self.solicitud.pk]), {'respuesta': 'rechazada'})
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado.codigo, EstadoSolicitud.APROBADA)

    def test_cotizacion_vencida_no_se_puede_aceptar(self):
        self.entrar_como_staff()
        self.client.post(reverse('panel_solicitud', args=[self.solicitud.pk]), {
            'accion': 'cotizacion', 'monto': '85000', 'plazo_dias': '3', 'validez_dias': '1', 'detalle': 'Detalle',
        })
        Cotizacion.objects.update(fecha_emision=timezone.now() - timedelta(days=5))
        self.client.force_login(self.cliente)
        self.client.post(reverse('responder_cotizacion', args=[self.solicitud.pk]), {'respuesta': 'aceptada'})
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado.codigo, EstadoSolicitud.COTIZADA)

    def test_cancelar_solicitud(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('cancelar_solicitud', args=[self.solicitud.pk]))
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado.codigo, EstadoSolicitud.CANCELADA)
        self.client.post(reverse('cancelar_solicitud', args=[self.solicitud.pk]))
        self.assertEqual(self.solicitud.historial.count(), 2)

    def test_gestion_interna(self):
        self.entrar_como_staff()
        self.client.post(reverse('panel_solicitud', args=[self.solicitud.pk]), {'accion': 'gestion', 'prioridad': 'alta', 'notas_internas': 'Llamar'})
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.prioridad, 'alta')
        self.client.force_login(self.cliente)
        self.assertNotContains(self.client.get(self.solicitud.get_absolute_url()), 'Llamar')

    def test_paginas_del_panel(self):
        self.entrar_como_staff()
        servicio = Servicio.objects.first()
        categoria = servicio.categoria
        rutas = [
            reverse('panel_inicio'), reverse('panel_solicitudes'), reverse('panel_solicitudes') + '?estado=recibida&tipo=Soporte&q=error',
            reverse('panel_solicitud', args=[self.solicitud.pk]), reverse('panel_servicios'), reverse('panel_servicio_nuevo'),
            reverse('panel_servicio_editar', args=[servicio.pk]), reverse('panel_categoria_nueva'),
            reverse('panel_categoria_editar', args=[categoria.pk]), reverse('panel_clientes'), reverse('panel_consultas'),
            reverse('ver_solicitud', args=[self.solicitud.pk]), reverse('admin:index'),
            reverse('admin:plataforma_solicitud_changelist'), reverse('admin:plataforma_solicitud_change', args=[self.solicitud.pk]),
        ]
        for ruta in rutas:
            self.assertEqual(self.client.get(ruta).status_code, 200, ruta)

    def test_crud_de_servicios(self):
        self.entrar_como_staff()
        respuesta = self.client.post(reverse('panel_servicio_nuevo'), {
            'nombre': 'Auditoría de accesibilidad', 'tipo': 'Mejora', 'categoria': '', 'resumen': 'Revisión de accesibilidad.',
            'descripcion': 'Revisamos tu sitio.', 'incluye': 'Informe', 'precio_base': '90000', 'plazo_referencial': '1 semana', 'activo': 'on',
        })
        self.assertRedirects(respuesta, reverse('panel_servicios'))
        servicio = Servicio.objects.get(nombre='Auditoría de accesibilidad')
        self.assertEqual(servicio.slug, 'auditoria-de-accesibilidad')
        self.client.post(reverse('panel_servicio_estado', args=[servicio.pk]))
        servicio.refresh_from_db()
        self.assertFalse(servicio.activo)
        respuesta = self.client.post(reverse('panel_categoria_nueva'), {'nombre': 'Consultoría', 'descripcion': '', 'icono': 'fa-solid fa-lightbulb', 'orden': '5', 'activa': 'on'})
        self.assertRedirects(respuesta, reverse('panel_servicios'))


class AsistenteTests(TestCase):
    def test_intenciones_principales(self):
        asistente = AsistenteVirtual()
        casos = {
            '¿Cuánto cuesta una página?': 'estimacion',
            'Quiero crear una página web para mi negocio': 'creacion',
            'Mi sitio está caído, no carga': 'soporte',
            'Necesito respaldos y actualizaciones': 'mantenimiento',
            'Quiero rediseñar mi sitio actual': 'mejora',
            '¿Cuánto se demoran?': 'plazos',
            'Quiero vender por internet con carrito': 'tienda',
            'hola': 'saludo',
            'xyzabc': 'no_entendido',
        }
        for mensaje, intencion in casos.items():
            self.assertEqual(asistente.responder(mensaje)['intencion'], intencion, mensaje)

    def test_endpoint_guarda_conversacion_de_visitante(self):
        respuesta = self.client.post(reverse('asistente_mensaje'), data='{"mensaje": "¿Cuánto cuesta?"}', content_type='application/json')
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(datos['intencion'], 'estimacion')
        self.assertTrue(datos['acciones'])
        self.assertEqual(MensajeAsistente.objects.count(), 2)
        historial = self.client.get(reverse('asistente_historial')).json()
        self.assertEqual(len(historial['mensajes']), 2)

    def test_endpoint_valida_entrada(self):
        self.assertEqual(self.client.post(reverse('asistente_mensaje'), data='no json', content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post(reverse('asistente_mensaje'), data='{"mensaje": "  "}', content_type='application/json').status_code, 400)
        self.assertEqual(self.client.get(reverse('asistente_mensaje')).status_code, 405)

    def test_historial_separado_por_usuario(self):
        cliente = crear_cliente()
        self.client.force_login(cliente)
        self.client.post(reverse('asistente_mensaje'), data='{"mensaje": "hola"}', content_type='application/json')
        self.client.force_login(crear_cliente('otro@correo.cl'))
        self.assertEqual(self.client.get(reverse('asistente_historial')).json()['mensajes'], [])


class ModeloTests(TestCase):
    def test_numero_correlativo_unico(self):
        cliente = crear_cliente()
        a = Solicitud.objects.create(cliente=cliente, tipo='Soporte', titulo='A', descripcion='x')
        b = Solicitud.objects.create(cliente=cliente, tipo='Soporte', titulo='B', descripcion='x')
        self.assertNotEqual(a.numero, b.numero)
        self.assertEqual(a.estado.codigo, EstadoSolicitud.RECIBIDA)

    def test_pasos_de_seguimiento(self):
        cliente = crear_cliente()
        s = Solicitud.objects.create(cliente=cliente, tipo='Soporte', titulo='A', descripcion='x', estado=EstadoSolicitud.obtener(EstadoSolicitud.COTIZADA))
        situaciones = [p['situacion'] for p in s.pasos_seguimiento]
        self.assertEqual(situaciones, ['hecho', 'hecho', 'actual', 'pendiente', 'pendiente', 'pendiente'])

    def test_datos_iniciales(self):
        self.assertEqual(EstadoSolicitud.objects.count(), 8)
        self.assertEqual(Servicio.objects.filter(activo=True).count(), 10)
