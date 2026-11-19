"""
Direcciones (URL) de la aplicación.

Están agrupadas igual que el diagrama de menús del informe (Tabla 31):
público, cuentas, solicitudes del cliente, asistente y panel del equipo.
El "name" de cada ruta es el que se usa en las plantillas con {% url %}.
"""

from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from .views import asistente, cliente, cuentas, panel, publico

urlpatterns = [
    # Páginas públicas (Visitante).
    path('', publico.inicio, name='inicio'),
    path('servicios/', publico.catalogo, name='catalogo'),
    path('servicios/<slug:slug>/', publico.servicio_detalle, name='servicio_detalle'),
    path('nosotros/', publico.nosotros, name='nosotros'),
    path('terminos/', publico.terminos, name='terminos'),
    path('privacidad/', publico.privacidad, name='privacidad'),
    path('robots.txt', publico.robots_txt, name='robots_txt'),
    path('salud/', publico.salud, name='salud'),

    # Cuentas: CU04 Registrarse, CU05 Iniciar sesión, CU07 Verificar código, CU14 Mi cuenta y CU06 Recuperar contraseña.
    path('cuenta/registro/', cuentas.registro, name='registro'),
    path('cuenta/ingresar/', cuentas.login_view, name='login'),
    path('cuenta/verificacion/', cuentas.verificar_codigo, name='verificar_codigo'),
    path('cuenta/verificacion/reenviar/', cuentas.reenviar_codigo, name='reenviar_codigo'),
    path('cuenta/salir/', cuentas.logout_view, name='logout'),
    path('cuenta/', cuentas.mi_cuenta, name='mi_cuenta'),
    path('cuenta/contrasena/', cuentas.cambiar_clave, name='cambiar_clave'),
    path('cuenta/mis-datos.json', cuentas.descargar_datos, name='descargar_datos'),
    path('cuenta/eliminar/', cuentas.eliminar_cuenta, name='eliminar_cuenta'),
    path('cuenta/recuperar/', cuentas.RecuperarClaveView.as_view(), name='recuperar_clave'),
    path(
        'cuenta/recuperar/enviado/',
        auth_views.PasswordResetDoneView.as_view(template_name='plataforma/auth/recuperar_enviado.html'),
        name='recuperar_enviado',
    ),
    path(
        'cuenta/recuperar/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='plataforma/auth/recuperar_confirmar.html',
            success_url=reverse_lazy('recuperar_completo'),
        ),
        name='restablecer_clave_confirmar',
    ),
    path(
        'cuenta/recuperar/listo/',
        auth_views.PasswordResetCompleteView.as_view(template_name='plataforma/auth/recuperar_completo.html'),
        name='recuperar_completo',
    ),

    # Solicitudes del cliente: CU08 a CU13.
    path('solicitudes/', cliente.mis_solicitudes, name='mis_solicitudes'),
    path('solicitudes/nueva/', cliente.nueva_solicitud, name='nueva_solicitud'),
    path('solicitudes/nueva/web/', cliente.crear_web, name='crear_web'),
    path('solicitudes/nueva/web/estimacion/', cliente.estimacion_web, name='estimacion_web'),
    path('solicitudes/nueva/mejora/', cliente.solicitar_mejora, name='solicitar_mejora'),
    path('solicitudes/nueva/soporte/', cliente.solicitar_soporte, name='solicitar_soporte'),
    path('solicitudes/nueva/mantenimiento/', cliente.solicitar_mantenimiento, name='solicitar_mantenimiento'),
    path('solicitudes/<int:pk>/', cliente.ver_solicitud, name='ver_solicitud'),
    path('solicitudes/<int:pk>/mensajes/', cliente.enviar_mensaje, name='enviar_mensaje'),
    path('solicitudes/<int:pk>/archivos/', cliente.subir_adjunto, name='subir_adjunto'),
    path('solicitudes/<int:pk>/cotizacion/', cliente.responder_cotizacion, name='responder_cotizacion'),
    path('solicitudes/<int:pk>/cotizacion/documento/', cliente.cotizacion_documento, name='cotizacion_documento'),
    path('solicitudes/<int:pk>/cancelar/', cliente.cancelar_solicitud, name='cancelar_solicitud'),
    path('archivos/<int:pk>/', cliente.descargar_adjunto, name='descargar_adjunto'),

    # Asistente virtual (CU03), usado desde las pantallas de solicitud.
    path('asistente/mensaje/', asistente.asistente_mensaje, name='asistente_mensaje'),
    path('asistente/historial/', asistente.asistente_historial, name='asistente_historial'),
    path('asistente/sugerencias/', asistente.asistente_sugerencias, name='asistente_sugerencias'),

    # Panel del equipo: CU15 a CU20.
    path('panel/', panel.panel_inicio, name='panel_inicio'),
    path('panel/solicitudes/', panel.panel_solicitudes, name='panel_solicitudes'),
    path('panel/tablero/', panel.panel_tablero, name='panel_tablero'),
    path('panel/solicitudes/<int:pk>/', panel.panel_solicitud, name='panel_solicitud'),
    path('panel/solicitudes/<int:pk>/mover/', panel.panel_mover_solicitud, name='panel_mover_solicitud'),
    path('panel/servicios/', panel.panel_servicios, name='panel_servicios'),
    path('panel/servicios/nuevo/', panel.panel_servicio_form, name='panel_servicio_nuevo'),
    path('panel/servicios/<int:pk>/editar/', panel.panel_servicio_form, name='panel_servicio_editar'),
    path('panel/servicios/<int:pk>/estado/', panel.panel_servicio_estado, name='panel_servicio_estado'),
    path('panel/categorias/nueva/', panel.panel_categoria_form, name='panel_categoria_nueva'),
    path('panel/categorias/<int:pk>/editar/', panel.panel_categoria_form, name='panel_categoria_editar'),
    path('panel/categorias/<int:pk>/estado/', panel.panel_categoria_estado, name='panel_categoria_estado'),
    path('panel/contenido/', panel.panel_contenido, name='panel_contenido'),
    path('panel/contenido/preguntas/nueva/', panel.panel_pregunta_form, name='panel_pregunta_nueva'),
    path('panel/contenido/preguntas/<int:pk>/editar/', panel.panel_pregunta_form, name='panel_pregunta_editar'),
    path('panel/contenido/preguntas/<int:pk>/estado/', panel.panel_pregunta_estado, name='panel_pregunta_estado'),
    path('panel/clientes/', panel.panel_clientes, name='panel_clientes'),
    path('panel/consultas/', panel.panel_consultas, name='panel_consultas'),
    path('panel/actividad/', panel.panel_actividad, name='panel_actividad'),
]
