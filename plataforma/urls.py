from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from .views import asistente, cliente, cuentas, panel, publico

urlpatterns = [
    path('', publico.inicio, name='inicio'),
    path('servicios/', publico.catalogo, name='catalogo'),
    path('servicios/<slug:slug>/', publico.servicio_detalle, name='servicio_detalle'),

    path('cuenta/registro/', cuentas.registro, name='registro'),
    path('cuenta/ingresar/', cuentas.login_view, name='login'),
    path('cuenta/verificacion/', cuentas.verificar_codigo, name='verificar_codigo'),
    path('cuenta/verificacion/reenviar/', cuentas.reenviar_codigo, name='reenviar_codigo'),
    path('cuenta/salir/', cuentas.logout_view, name='logout'),
    path('cuenta/', cuentas.mi_cuenta, name='mi_cuenta'),
    path(
        'cuenta/recuperar/',
        auth_views.PasswordResetView.as_view(
            template_name='plataforma/auth/recuperar.html',
            email_template_name='plataforma/correos/restablecer_clave.txt',
            subject_template_name='plataforma/correos/restablecer_clave_asunto.txt',
            success_url=reverse_lazy('recuperar_enviado'),
        ),
        name='recuperar_clave',
    ),
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

    path('solicitudes/', cliente.mis_solicitudes, name='mis_solicitudes'),
    path('solicitudes/nueva/', cliente.nueva_solicitud, name='nueva_solicitud'),
    path('solicitudes/nueva/web/', cliente.crear_web, name='crear_web'),
    path('solicitudes/nueva/web/estimacion/', cliente.estimacion_web, name='estimacion_web'),
    path('solicitudes/nueva/mejora/', cliente.solicitar_mejora, name='solicitar_mejora'),
    path('solicitudes/nueva/soporte/', cliente.solicitar_soporte, name='solicitar_soporte'),
    path('solicitudes/nueva/mantenimiento/', cliente.solicitar_mantenimiento, name='solicitar_mantenimiento'),
    path('solicitudes/<int:pk>/', cliente.ver_solicitud, name='ver_solicitud'),
    path('solicitudes/<int:pk>/cotizacion/', cliente.responder_cotizacion, name='responder_cotizacion'),
    path('solicitudes/<int:pk>/cancelar/', cliente.cancelar_solicitud, name='cancelar_solicitud'),

    path('asistente/mensaje/', asistente.asistente_mensaje, name='asistente_mensaje'),
    path('asistente/historial/', asistente.asistente_historial, name='asistente_historial'),

    path('panel/', panel.panel_inicio, name='panel_inicio'),
    path('panel/solicitudes/', panel.panel_solicitudes, name='panel_solicitudes'),
    path('panel/solicitudes/<int:pk>/', panel.panel_solicitud, name='panel_solicitud'),
    path('panel/servicios/', panel.panel_servicios, name='panel_servicios'),
    path('panel/servicios/nuevo/', panel.panel_servicio_form, name='panel_servicio_nuevo'),
    path('panel/servicios/<int:pk>/editar/', panel.panel_servicio_form, name='panel_servicio_editar'),
    path('panel/servicios/<int:pk>/estado/', panel.panel_servicio_estado, name='panel_servicio_estado'),
    path('panel/categorias/nueva/', panel.panel_categoria_form, name='panel_categoria_nueva'),
    path('panel/categorias/<int:pk>/editar/', panel.panel_categoria_form, name='panel_categoria_editar'),
    path('panel/categorias/<int:pk>/estado/', panel.panel_categoria_estado, name='panel_categoria_estado'),
    path('panel/clientes/', panel.panel_clientes, name='panel_clientes'),
    path('panel/consultas/', panel.panel_consultas, name='panel_consultas'),
]
