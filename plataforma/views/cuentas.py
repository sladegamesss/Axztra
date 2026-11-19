"""
Vistas de cuentas: registro, inicio de sesión y cuenta del cliente.

Siguen el diagrama de actividades DA-01 (Autenticación) del informe.
Casos de uso: CU04 Registrarse, CU05 Iniciar sesión, CU06 Recuperar contraseña,
CU07 Verificar código de acceso y CU14 Gestionar mi cuenta.
"""

import json
import logging
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError, transaction
from django.db.models.functions import Lower
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .. import auditoria, notificaciones
from ..forms import CambioClaveForm, CodigoVerificacionForm, CuentaForm, EliminarCuentaForm, LoginForm, RegistroForm
from ..models import CodigoVerificacion, EstadoSolicitud, MensajeAsistente, PerfilCliente
from ..seguridad import bloqueado, contar, excede, ip_cliente, limitar, reiniciar, respuesta_limite
from ..verificacion import (
    CLAVE_SESION_DESTINO,
    CLAVE_SESION_PENDIENTE,
    generar_codigo,
    marcar_sesion_verificada,
    requiere_verificacion,
    sesion_verificada,
    validar_codigo,
)

User = get_user_model()
logger = logging.getLogger('plataforma.seguridad')

INTENTOS_POR_CORREO = 5
INTENTOS_POR_IP = 30
VENTANA_BLOQUEO = 15 * 60


# Solo permite redirigir a páginas del mismo sitio después de iniciar sesión.
def _destino_seguro(request, destino, defecto='inicio'):
    if destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return destino
    return reverse(defecto)


# Muestra el correo parcialmente oculto en la pantalla del código (ej: ad***@axztra.cl).
def _ocultar_correo(correo):
    usuario, _, dominio = (correo or '').partition('@')
    if not dominio:
        return correo
    visible = usuario[:2] if len(usuario) > 2 else usuario[:1]
    return f"{visible}{'*' * max(3, len(usuario) - len(visible))}@{dominio}"


# CU04 Registrarse: crea la cuenta y confirma el correo con un código (CU07) antes de iniciar la sesión.
@limitar('registro', 10, 3600)
def registro(request):
    if request.user.is_authenticated:
        return redirect('inicio')
    destino = request.POST.get('next') or request.GET.get('next', '')
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    usuario = form.save()
            except IntegrityError:
                form.add_error('email', 'Ya existe una cuenta con este correo. Inicia sesión o recupera tu contraseña.')
            else:
                notificaciones.bienvenida(usuario, request)
                if requiere_verificacion(usuario):
                    # El código confirma que el correo es real; la sesión se abre recién al ingresarlo.
                    if notificaciones.codigo_verificacion(usuario, generar_codigo(usuario)):
                        request.session[CLAVE_SESION_PENDIENTE] = usuario.pk
                        request.session[CLAVE_SESION_DESTINO] = destino or reverse('nueva_solicitud')
                        messages.success(request, f'Bienvenido, {usuario.first_name}. Tu cuenta quedó creada; confirma tu correo con el código que te enviamos.')
                        return redirect('verificar_codigo')
                    messages.warning(request, 'Tu cuenta quedó creada, pero no pudimos enviar el código. Inicia sesión para recibir uno nuevo.')
                    return redirect('login')
                login(request, usuario, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, f'Bienvenido, {usuario.first_name}. Tu cuenta quedó creada.')
                return redirect(_destino_seguro(request, destino, 'nueva_solicitud'))
    else:
        form = RegistroForm()
    return render(request, 'plataforma/auth/registro.html', {'form': form, 'next': destino})


# CU05 Iniciar sesión (DA-01): bloquea por 15 minutos tras 5 intentos fallidos.
# Después de la contraseña envía un código por correo y pasa a CU07 (clientes y equipo) antes de abrir la sesión.
def login_view(request):
    destino = request.POST.get('next') or request.GET.get('next', '')
    if request.user.is_authenticated:
        if requiere_verificacion(request.user) and not sesion_verificada(request):
            return redirect(f"{reverse('verificar_codigo')}?{urlencode({'next': destino})}")
        return redirect(_destino_seguro(request, destino))

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            correo = form.cleaned_data['email']
            ip = ip_cliente(request)
            if bloqueado(f'login-correo:{correo}', INTENTOS_POR_CORREO) or bloqueado(f'login-ip:{ip}', INTENTOS_POR_IP):
                logger.warning('Ingreso bloqueado temporalmente para %s desde %s', correo, ip)
                form.add_error(None, 'Hubo demasiados intentos fallidos. Espera 15 minutos o recupera tu contraseña.')
            else:
                candidato = User.objects.annotate(correo_normalizado=Lower('email')).filter(correo_normalizado=correo).order_by('pk').first()
                usuario = None
                if candidato is not None:
                    usuario = authenticate(request, username=candidato.get_username(), password=form.cleaned_data['password'])
                if usuario is None:
                    contar(f'login-correo:{correo}', VENTANA_BLOQUEO)
                    contar(f'login-ip:{ip}', VENTANA_BLOQUEO)
                    logger.info('Intento de ingreso fallido para %s desde %s', correo, ip)
                    form.add_error(None, 'El correo o la contraseña no son correctos.')
                else:
                    reiniciar(f'login-correo:{correo}')
                    if requiere_verificacion(usuario):
                        codigo = generar_codigo(usuario)
                        if not notificaciones.codigo_verificacion(usuario, codigo):
                            form.add_error(None, 'No pudimos enviar el código de verificación. Revisa la configuración de correo.')
                        else:
                            request.session[CLAVE_SESION_PENDIENTE] = usuario.pk
                            request.session[CLAVE_SESION_DESTINO] = destino
                            return redirect('verificar_codigo')
                    else:
                        login(request, usuario)
                        PerfilCliente.objects.get_or_create(usuario=usuario)
                        messages.success(request, f'Hola de nuevo, {usuario.first_name or usuario.email}.')
                        return redirect(_destino_seguro(request, destino))
    else:
        form = LoginForm()
    return render(request, 'plataforma/auth/login.html', {'form': form, 'next': destino})


# Usuario que inició sesión pero todavía no ingresa el código de verificación.
def _usuario_en_verificacion(request):
    if request.user.is_authenticated:
        if requiere_verificacion(request.user) and not sesion_verificada(request):
            return request.user, True
        return None, True
    pendiente = request.session.get(CLAVE_SESION_PENDIENTE)
    if pendiente:
        return User.objects.filter(pk=pendiente, is_active=True).first(), False
    return None, False


# CU07 Verificar código de acceso: valida el código de 6 dígitos (vigencia 10 minutos, 5 intentos). Lo usan clientes y equipo.
def verificar_codigo(request):
    usuario, ya_autenticado = _usuario_en_verificacion(request)
    if usuario is None:
        if ya_autenticado:
            return redirect(_destino_seguro(request, request.GET.get('next'), 'panel_inicio' if request.user.is_staff else 'inicio'))
        messages.info(request, 'Ingresa con tu correo y contraseña para continuar.')
        return redirect('login')

    if request.GET.get('next'):
        request.session[CLAVE_SESION_DESTINO] = request.GET['next']

    if request.method == 'GET' and ya_autenticado and not CodigoVerificacion.objects.filter(usuario=usuario, usado=False).exists():
        notificaciones.codigo_verificacion(usuario, generar_codigo(usuario))

    if request.method == 'POST':
        if excede(f'verificacion:{usuario.pk}', 15, 600):
            return respuesta_limite(request)
        form = CodigoVerificacionForm(request.POST)
        if form.is_valid():
            valido, error = validar_codigo(usuario, form.cleaned_data['codigo'])
            if valido:
                destino = request.session.pop(CLAVE_SESION_DESTINO, '')
                request.session.pop(CLAVE_SESION_PENDIENTE, None)
                if not ya_autenticado:
                    login(request, usuario, backend='django.contrib.auth.backends.ModelBackend')
                marcar_sesion_verificada(request)
                if usuario.is_staff:
                    auditoria.registrar(request, 'acceso', 'Ingreso al panel con verificación en dos pasos', usuario=usuario)
                    messages.success(request, 'Identidad verificada. Bienvenido al panel de administración.')
                    return redirect(_destino_seguro(request, destino, 'panel_inicio'))
                PerfilCliente.objects.get_or_create(usuario=usuario)
                messages.success(request, f'Identidad verificada. Hola, {usuario.first_name or usuario.email}.')
                return redirect(_destino_seguro(request, destino, 'inicio'))
            logger.info('Código de verificación incorrecto para %s', usuario.email)
            form.add_error('codigo', error)
    else:
        form = CodigoVerificacionForm()

    return render(request, 'plataforma/auth/verificar_codigo.html', {
        'form': form,
        'correo_oculto': _ocultar_correo(usuario.email),
    })


# Envía un código nuevo si el anterior venció o se agotaron los intentos.
@require_POST
def reenviar_codigo(request):
    usuario, _ = _usuario_en_verificacion(request)
    if usuario is None:
        return redirect('login')
    if excede(f'reenvio-codigo:{usuario.pk}', 3, 600):
        messages.error(request, 'Ya enviamos varios códigos. Espera unos minutos antes de pedir otro.')
        return redirect('verificar_codigo')
    notificaciones.codigo_verificacion(usuario, generar_codigo(usuario))
    messages.info(request, 'Te enviamos un código nuevo. El anterior dejó de ser válido.')
    return redirect('verificar_codigo')


# Cierra la sesión (solo por POST, para evitar cierres accidentales).
@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, 'Cerraste sesión correctamente.')
    return redirect('inicio')


# CU06 Recuperar contraseña: envía un enlace para crear una nueva.
class RecuperarClaveView(auth_views.PasswordResetView):
    template_name = 'plataforma/auth/recuperar.html'
    email_template_name = 'plataforma/correos/restablecer_clave.txt'
    subject_template_name = 'plataforma/correos/restablecer_clave_asunto.txt'
    success_url = reverse_lazy('recuperar_enviado')

    def post(self, request, *args, **kwargs):
        if excede(f'recuperar:{ip_cliente(request)}', 5, 900):
            return respuesta_limite(request)
        return super().post(request, *args, **kwargs)


# CU14 Gestionar mi cuenta: datos personales del cliente.
@login_required
def mi_cuenta(request):
    perfil, _ = PerfilCliente.objects.get_or_create(usuario=request.user)
    if request.method == 'POST':
        form = CuentaForm(request.POST, instance=perfil, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tus datos se actualizaron correctamente.')
            return redirect('mi_cuenta')
    else:
        form = CuentaForm(instance=perfil, usuario=request.user)
    solicitudes = request.user.solicitudes.all()
    return render(request, 'plataforma/cliente/mi_cuenta.html', {
        'form': form,
        'total_solicitudes': solicitudes.count(),
        'solicitudes_activas': solicitudes.filter(estado__es_final=False).count(),
    })


# Cambio de contraseña desde Mi cuenta.
@login_required
def cambiar_clave(request):
    if request.method == 'POST':
        form = CambioClaveForm(request.user, request.POST)
        if form.is_valid():
            usuario = form.save()
            update_session_auth_hash(request, usuario)
            messages.success(request, 'Tu contraseña se actualizó correctamente.')
            return redirect('mi_cuenta')
    else:
        form = CambioClaveForm(request.user)
    return render(request, 'plataforma/cliente/cambiar_clave.html', {'form': form})


# Entrega todos los datos del cliente en un archivo JSON (Ley 19.628).
@login_required
def descargar_datos(request):
    usuario = request.user
    perfil = getattr(usuario, 'perfil_cliente', None)
    solicitudes = []
    for s in usuario.solicitudes.select_related('estado', 'servicio', 'requerimiento', 'estimacion', 'cotizacion').prefetch_related('historial__estado_nuevo', 'mensajes', 'adjuntos'):
        requerimiento = s.requerimiento
        estimacion = getattr(s, 'estimacion', None)
        cotizacion = getattr(s, 'cotizacion', None)
        solicitudes.append({
            'numero': s.numero,
            'titulo': s.titulo,
            'tipo': s.get_tipo_display(),
            'estado': s.estado.nombre,
            'servicio': s.servicio.nombre if s.servicio_id else None,
            'descripcion': s.descripcion,
            'sitio_web': s.url_sitio,
            'detalles': s.detalles,
            'fecha_solicitud': s.fecha_solicitud,
            'requerimiento': None if requerimiento is None else {
                'negocio': requerimiento.nombre_negocio,
                'rubro': requerimiento.nombre_rubro,
                'tipo_sitio': requerimiento.get_tipo_sitio_display(),
                'objetivos': requerimiento.objetivos,
                'funcionalidades': requerimiento.funcionalidades,
                'integraciones': requerimiento.integraciones,
                'paginas': requerimiento.num_paginas,
            },
            'estimacion': None if estimacion is None else {'minimo': estimacion.monto_minimo, 'maximo': estimacion.monto_maximo},
            'cotizacion': None if cotizacion is None else {
                'neto': cotizacion.monto,
                'total': cotizacion.total,
                'items': cotizacion.items,
                'respuesta': cotizacion.respuesta_cliente,
            },
            'historial': [{'estado': h.estado_nuevo.nombre, 'comentario': h.comentario, 'fecha': h.fecha} for h in s.historial.all()],
            'mensajes': [{'autor': 'Equipo AXZTRA' if m.es_equipo else 'Cliente', 'texto': m.texto, 'fecha': m.fecha} for m in s.mensajes.all()],
            'archivos': [a.nombre_original for a in s.adjuntos.all()],
        })
    datos = {
        'generado': timezone.now(),
        'cuenta': {
            'nombre': usuario.first_name,
            'apellido': usuario.last_name,
            'correo': usuario.email,
            'fecha_registro': usuario.date_joined,
        },
        'perfil': None if perfil is None else {
            'empresa': perfil.empresa,
            'rut': perfil.rut,
            'telefono': perfil.telefono,
            'ciudad': perfil.ciudad,
            'recibir_notificaciones': perfil.recibir_notificaciones,
            'aceptacion_terminos': perfil.fecha_aceptacion_terminos,
        },
        'solicitudes': solicitudes,
        'consultas_asistente': list(
            MensajeAsistente.objects.filter(usuario=usuario, es_asistente=False).values('contenido', 'fecha')
        ),
    }
    contenido = json.dumps(datos, cls=DjangoJSONEncoder, ensure_ascii=False, indent=2)
    respuesta = HttpResponse(contenido, content_type='application/json; charset=utf-8')
    respuesta['Content-Disposition'] = 'attachment; filename="mis-datos-axztra.json"'
    return respuesta


# Elimina la cuenta: borra los datos personales y conserva las solicitudes de forma anónima.
@login_required
def eliminar_cuenta(request):
    usuario = request.user
    activas = usuario.solicitudes.exclude(estado__es_final=True).exclude(estado__codigo=EstadoSolicitud.RECHAZADA).count()
    if request.method == 'POST':
        form = EliminarCuentaForm(request.POST, usuario=usuario)
        if activas:
            messages.error(request, 'Antes de eliminar tu cuenta, cancela o finaliza tus solicitudes en curso.')
        elif form.is_valid():
            with transaction.atomic():
                auditoria.registrar(request, 'cuenta', f'Cuenta eliminada a petición del usuario #{usuario.pk}', usuario=None)
                MensajeAsistente.objects.filter(usuario=usuario).delete()
                PerfilCliente.objects.filter(usuario=usuario).update(empresa='', rut='', telefono='', ciudad='', recibir_notificaciones=False)
                usuario.email = f'eliminado-{usuario.pk}@axztra.invalid'
                usuario.username = usuario.email
                usuario.first_name = 'Cuenta'
                usuario.last_name = 'eliminada'
                usuario.is_active = False
                usuario.set_unusable_password()
                usuario.save()
            logout(request)
            messages.success(request, 'Tu cuenta y tus datos personales fueron eliminados.')
            return redirect('inicio')
    else:
        form = EliminarCuentaForm(usuario=usuario)
    return render(request, 'plataforma/cliente/eliminar_cuenta.html', {'form': form, 'activas': activas})
