from functools import wraps
from urllib.parse import urlencode

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from .verificacion import sesion_verificada


def staff_verificado(vista):
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?{urlencode({'next': request.get_full_path()})}")
        if not request.user.is_staff:
            messages.error(request, 'Tu cuenta no tiene acceso al panel de administración.')
            return redirect('inicio')
        if not sesion_verificada(request):
            return redirect(f"{reverse('verificar_codigo')}?{urlencode({'next': request.get_full_path()})}")
        return vista(request, *args, **kwargs)

    return envoltura
