from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .. import notificaciones
from ..forms import CodigoVerificacionForm, CuentaForm, LoginForm, RegistroForm
from ..models import CodigoVerificacion, PerfilCliente
from ..verificacion import (
    CLAVE_SESION_DESTINO,
    CLAVE_SESION_PENDIENTE,
    generar_codigo,
    marcar_sesion_verificada,
    sesion_verificada,
    validar_codigo,
)

User = get_user_model()


def _destino_seguro(request, destino, defecto='inicio'):
    if destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return destino
    return reverse(defecto)


def _ocultar_correo(correo):
    usuario, _, dominio = (correo or '').partition('@')
    if not dominio:
        return correo
    visible = usuario[:2] if len(usuario) > 2 else usuario[:1]
    return f"{visible}{'•' * max(3, len(usuario) - len(visible))}@{dominio}"


def registro(request):
    if request.user.is_authenticated:
        return redirect('inicio')
    destino = request.POST.get('next') or request.GET.get('next', '')
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario, backend='django.contrib.auth.backends.ModelBackend')
            notificaciones.bienvenida(usuario, request)
            messages.success(request, f'Bienvenido, {usuario.first_name}. Tu cuenta quedó creada.')
            return redirect(_destino_seguro(request, destino, 'nueva_solicitud'))
    else:
        form = RegistroForm()
    return render(request, 'plataforma/auth/registro.html', {'form': form, 'next': destino})


def login_view(request):
    destino = request.POST.get('next') or request.GET.get('next', '')
    if request.user.is_authenticated:
        if request.user.is_staff and not sesion_verificada(request):
            return redirect(f"{reverse('verificar_codigo')}?{urlencode({'next': destino})}")
        return redirect(_destino_seguro(request, destino))

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            candidato = User.objects.filter(email__iexact=form.cleaned_data['email']).order_by('pk').first()
            usuario = None
            if candidato is not None:
                usuario = authenticate(request, username=candidato.get_username(), password=form.cleaned_data['password'])
            if usuario is None:
                form.add_error(None, 'El correo o la contraseña no son correctos.')
            elif usuario.is_staff:
                codigo = generar_codigo(usuario)
                enviado = notificaciones.codigo_verificacion(usuario, codigo)
                if not enviado:
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


def _usuario_en_verificacion(request):
    if request.user.is_authenticated:
        if request.user.is_staff and not sesion_verificada(request):
            return request.user, True
        return None, True
    pendiente = request.session.get(CLAVE_SESION_PENDIENTE)
    if pendiente:
        return User.objects.filter(pk=pendiente, is_active=True, is_staff=True).first(), False
    return None, False


def verificar_codigo(request):
    usuario, ya_autenticado = _usuario_en_verificacion(request)
    if usuario is None:
        if ya_autenticado:
            return redirect(_destino_seguro(request, request.GET.get('next'), 'panel_inicio'))
        messages.info(request, 'Ingresa con tu correo y contraseña para continuar.')
        return redirect('login')

    if request.GET.get('next'):
        request.session[CLAVE_SESION_DESTINO] = request.GET['next']

    if request.method == 'GET' and ya_autenticado and not CodigoVerificacion.objects.filter(usuario=usuario, usado=False).exists():
        notificaciones.codigo_verificacion(usuario, generar_codigo(usuario))

    if request.method == 'POST':
        form = CodigoVerificacionForm(request.POST)
        if form.is_valid():
            valido, error = validar_codigo(usuario, form.cleaned_data['codigo'])
            if valido:
                destino = request.session.pop(CLAVE_SESION_DESTINO, '')
                request.session.pop(CLAVE_SESION_PENDIENTE, None)
                if not ya_autenticado:
                    login(request, usuario, backend='django.contrib.auth.backends.ModelBackend')
                marcar_sesion_verificada(request)
                messages.success(request, 'Identidad verificada. Bienvenido al panel de administración.')
                return redirect(_destino_seguro(request, destino, 'panel_inicio'))
            form.add_error('codigo', error)
    else:
        form = CodigoVerificacionForm()

    return render(request, 'plataforma/auth/verificar_codigo.html', {
        'form': form,
        'correo_oculto': _ocultar_correo(usuario.email),
    })


@require_POST
def reenviar_codigo(request):
    usuario, _ = _usuario_en_verificacion(request)
    if usuario is None:
        return redirect('login')
    notificaciones.codigo_verificacion(usuario, generar_codigo(usuario))
    messages.info(request, 'Te enviamos un código nuevo. El anterior dejó de ser válido.')
    return redirect('verificar_codigo')


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, 'Cerraste sesión correctamente.')
    return redirect('inicio')


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
    solicitudes = request.user.solicitudes.select_related('estado')
    return render(request, 'plataforma/cliente/mi_cuenta.html', {
        'form': form,
        'total_solicitudes': solicitudes.count(),
        'solicitudes_activas': solicitudes.filter(estado__es_final=False).count(),
    })
