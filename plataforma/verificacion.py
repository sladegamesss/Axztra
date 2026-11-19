"""
Verificación en dos pasos para todos los usuarios (RNF04, CU07 Verificar código de acceso).

Después de la contraseña se envía un código de 6 dígitos al correo. Vence en 10 minutos
y permite 5 intentos. Solo se guarda su huella, nunca el código.
El equipo siempre se verifica; los clientes también, salvo que se desactive con AXZTRA_VERIFICACION_CLIENTES=0.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

CLAVE_SESION_VERIFICADA = 'axztra_verificacion_ok'
CLAVE_SESION_PENDIENTE = 'axztra_verificacion_pendiente'
CLAVE_SESION_DESTINO = 'axztra_verificacion_destino'


# Indica si este usuario debe ingresar un código al iniciar sesión (todo el equipo y, por defecto, los clientes).
def requiere_verificacion(usuario):
    return usuario.is_staff or settings.AXZTRA['VERIFICACION_CLIENTES']


# Indica si la sesión actual ya pasó la verificación.
def sesion_verificada(request):
    return (
        request.user.is_authenticated
        and request.session.get(CLAVE_SESION_VERIFICADA) == request.user.pk
    )


# Marca la sesión como verificada después de un código correcto.
def marcar_sesion_verificada(request):
    request.session[CLAVE_SESION_VERIFICADA] = request.user.pk


# Crea un código nuevo, invalida los anteriores y lo envía por correo.
def generar_codigo(usuario):
    from .models import CodigoVerificacion

    CodigoVerificacion.objects.filter(usuario=usuario, usado=False).update(usado=True)
    codigo = f'{secrets.randbelow(1000000):06d}'
    minutos = settings.AXZTRA['CODIGO_VERIFICACION_MINUTOS']
    CodigoVerificacion.objects.create(
        usuario=usuario,
        codigo_hash=make_password(codigo),
        expira=timezone.now() + timedelta(minutes=minutos),
    )
    return codigo


# Revisa el código ingresado y descuenta intentos.
def validar_codigo(usuario, codigo):
    from .models import CodigoVerificacion

    registro = CodigoVerificacion.objects.filter(usuario=usuario, usado=False).first()
    if registro is None:
        return False, 'No hay un código activo. Solicita uno nuevo.'
    if timezone.now() > registro.expira:
        registro.usado = True
        registro.save(update_fields=['usado'])
        return False, 'El código expiró. Solicita uno nuevo.'
    limite = settings.AXZTRA['CODIGO_VERIFICACION_INTENTOS']
    if registro.intentos >= limite:
        registro.usado = True
        registro.save(update_fields=['usado'])
        return False, 'Superaste el número de intentos permitidos. Solicita un código nuevo.'
    if not check_password((codigo or '').strip(), registro.codigo_hash):
        registro.intentos += 1
        registro.save(update_fields=['intentos'])
        restantes = limite - registro.intentos
        if restantes <= 0:
            return False, 'Código incorrecto. Solicita un código nuevo.'
        return False, f'Código incorrecto. Te quedan {restantes} intentos.'
    registro.usado = True
    registro.save(update_fields=['usado'])
    return True, ''
