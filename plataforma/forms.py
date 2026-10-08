"""
Formularios de AXZTRA.

Aquí se definen los campos que ve el usuario y las validaciones del lado del servidor.
Las mismas reglas se repiten en el navegador (static/js/app.js) para avisar antes de enviar (RNF05).
"""

import os
import re
import uuid

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.db.models.functions import Lower
from django.forms import formset_factory
from django.utils import timezone

from .estimacion import FUNCIONALIDADES, INTEGRACIONES, MAXIMO_PAGINAS, OBJETIVOS, RUBROS
from .models import (
    Categoria,
    ConfiguracionSitio,
    Cotizacion,
    EstadoSolicitud,
    PerfilCliente,
    PreguntaFrecuente,
    RequerimientoWeb,
    Servicio,
    Solicitud,
)

User = get_user_model()

CAMPO_URL = forms.TextInput(attrs={'inputmode': 'url', 'autocomplete': 'url', 'placeholder': 'https://www.tusitio.cl'})


# Agrega las clases CSS y atributos comunes a todos los campos de un formulario.
class EstiloFormularioMixin:
    def aplicar_estilos(self):
        for campo in self.fields.values():
            widget = campo.widget
            if isinstance(widget, (forms.CheckboxSelectMultiple, forms.RadioSelect, forms.HiddenInput)):
                continue
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', 'casilla')
            else:
                widget.attrs.setdefault('class', 'control')


# Valida el RUT chileno con su dígito verificador.
def validar_rut(valor):
    limpio = re.sub(r'[^0-9kK]', '', valor or '').upper()
    if not limpio:
        return ''
    if len(limpio) < 2:
        raise forms.ValidationError('Ingresa un RUT válido.')
    cuerpo, dv = limpio[:-1], limpio[-1]
    if not cuerpo.isdigit():
        raise forms.ValidationError('Ingresa un RUT válido.')
    suma, multiplicador = 0, 2
    for digito in reversed(cuerpo):
        suma += int(digito) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1
    resto = 11 - (suma % 11)
    esperado = {11: '0', 10: 'K'}.get(resto, str(resto))
    if dv != esperado:
        raise forms.ValidationError('El dígito verificador del RUT no es correcto.')
    cuerpo_formateado = f'{int(cuerpo):,}'.replace(',', '.')
    return f'{cuerpo_formateado}-{dv}'


# Acepta teléfonos chilenos con o sin +56.
def validar_telefono(valor):
    valor = (valor or '').strip()
    if not valor:
        return ''
    digitos = re.sub(r'\D', '', valor)
    if len(digitos) < 8 or len(digitos) > 12:
        raise forms.ValidationError('Ingresa un teléfono válido, por ejemplo +56 9 1234 5678.')
    return valor


# Impide elegir una fecha que ya pasó.
def validar_fecha_futura(fecha):
    if fecha and fecha < timezone.localdate():
        raise forms.ValidationError('La fecha deseada no puede estar en el pasado.')
    return fecha


# Revisa extensión y tamaño de los archivos adjuntos.
def validar_archivo(archivo):
    if not archivo:
        return archivo
    extensiones = settings.AXZTRA['ADJUNTOS_EXTENSIONES']
    maximo = settings.AXZTRA['ADJUNTOS_MAXIMO_MB']
    extension = os.path.splitext(archivo.name)[1].lower().lstrip('.')
    if extension not in extensiones:
        raise forms.ValidationError(f'Formato no permitido. Usa: {", ".join(extensiones)}.')
    if archivo.size > maximo * 1024 * 1024:
        raise forms.ValidationError(f'El archivo supera el máximo de {maximo} MB.')
    if archivo.size == 0:
        raise forms.ValidationError('El archivo está vacío.')
    return archivo


# Texto que explica qué archivos se aceptan.
def texto_ayuda_adjuntos():
    return (
        f"Opcional. Hasta {settings.AXZTRA['ADJUNTOS_MAXIMO_MB']} MB en formato "
        f"{', '.join(settings.AXZTRA['ADJUNTOS_EXTENSIONES'])}."
    )


# CU04 Registrarse: crea el usuario y su perfil de cliente.
class RegistroForm(EstiloFormularioMixin, UserCreationForm):
    first_name = forms.CharField(label='Nombre', max_length=80)
    last_name = forms.CharField(label='Apellido', max_length=80)
    email = forms.EmailField(label='Correo electrónico')
    empresa = forms.CharField(label='Empresa o emprendimiento', max_length=200, required=False)
    telefono = forms.CharField(label='Teléfono', max_length=20, required=False)
    acepta_terminos = forms.BooleanField(
        label='Acepto los términos de uso y la política de privacidad',
        error_messages={'required': 'Debes aceptar los términos y la política de privacidad para crear la cuenta.'},
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = 'Contraseña'
        self.fields['password2'].label = 'Repite la contraseña'
        self.fields['password1'].help_text = 'Mínimo 8 caracteres, que no sean solo números ni se parezcan a tus datos.'
        self.fields['password2'].help_text = ''
        self.aplicar_estilos()
        self.fields['first_name'].widget.attrs.update({'autocomplete': 'given-name'})
        self.fields['last_name'].widget.attrs.update({'autocomplete': 'family-name'})
        self.fields['email'].widget.attrs.update({'autocomplete': 'email', 'placeholder': 'nombre@empresa.cl'})
        self.fields['telefono'].widget.attrs.update({'placeholder': '+56 9 1234 5678', 'autocomplete': 'tel', 'inputmode': 'tel'})
        self.fields['empresa'].widget.attrs.update({'autocomplete': 'organization'})

    # Evita dos cuentas con el mismo correo (sin distinguir mayúsculas).
    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.annotate(correo_normalizado=Lower('email')).filter(correo_normalizado=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este correo. Inicia sesión o recupera tu contraseña.')
        return email

    def clean_telefono(self):
        return validar_telefono(self.cleaned_data.get('telefono'))

    # Guarda el usuario (el correo es también su nombre de usuario) y crea su PerfilCliente.
    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.username = self.cleaned_data['email'][:150]
        usuario.email = self.cleaned_data['email']
        if commit:
            usuario.save()
            PerfilCliente.objects.update_or_create(
                usuario=usuario,
                defaults={
                    'empresa': self.cleaned_data.get('empresa', ''),
                    'telefono': self.cleaned_data.get('telefono', ''),
                    'fecha_aceptacion_terminos': timezone.now(),
                },
            )
        return usuario


# CU05 Iniciar sesión con correo y contraseña.
class LoginForm(EstiloFormularioMixin, forms.Form):
    email = forms.EmailField(label='Correo electrónico')
    password = forms.CharField(label='Contraseña', widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos()
        self.fields['email'].widget.attrs.update({'autocomplete': 'email', 'placeholder': 'nombre@empresa.cl', 'autofocus': True})
        self.fields['password'].widget.attrs.update({'autocomplete': 'current-password'})

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()


# CU07 Verificar código de acceso: código de 6 dígitos para clientes y equipo.
class CodigoVerificacionForm(EstiloFormularioMixin, forms.Form):
    codigo = forms.RegexField(
        label='Código de 6 dígitos',
        regex=r'^\s*\d{6}\s*$',
        error_messages={'invalid': 'El código debe tener 6 dígitos.'},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos()
        self.fields['codigo'].widget.attrs.update({
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code',
            'maxlength': 6,
            'pattern': r'\d{6}',
            'class': 'control control-codigo',
            'autofocus': True,
        })


# CU14 Gestionar mi cuenta: datos personales del cliente.
class CuentaForm(EstiloFormularioMixin, forms.ModelForm):
    first_name = forms.CharField(label='Nombre', max_length=80)
    last_name = forms.CharField(label='Apellido', max_length=80)

    class Meta:
        model = PerfilCliente
        fields = ['empresa', 'rut', 'telefono', 'ciudad', 'recibir_notificaciones']
        labels = {'recibir_notificaciones': 'Recibir avisos por correo cuando cambie el estado de mis solicitudes'}

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)
        if usuario is not None:
            self.fields['first_name'].initial = usuario.first_name
            self.fields['last_name'].initial = usuario.last_name
        orden = ['first_name', 'last_name', 'empresa', 'rut', 'telefono', 'ciudad', 'recibir_notificaciones']
        self.fields = {nombre: self.fields[nombre] for nombre in orden}
        self.aplicar_estilos()
        self.fields['rut'].widget.attrs['placeholder'] = '12.345.678-9'
        self.fields['telefono'].widget.attrs.update({'inputmode': 'tel', 'autocomplete': 'tel'})

    def clean_rut(self):
        return validar_rut(self.cleaned_data.get('rut'))

    def clean_telefono(self):
        return validar_telefono(self.cleaned_data.get('telefono'))

    def save(self, commit=True):
        perfil = super().save(commit=False)
        if self.usuario is not None:
            self.usuario.first_name = self.cleaned_data['first_name']
            self.usuario.last_name = self.cleaned_data['last_name']
            if commit:
                self.usuario.save(update_fields=['first_name', 'last_name'])
        if commit:
            perfil.save()
        return perfil


# Cambio de contraseña desde Mi cuenta.
class CambioClaveForm(EstiloFormularioMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].label = 'Contraseña actual'
        self.fields['new_password1'].label = 'Contraseña nueva'
        self.fields['new_password2'].label = 'Repite la contraseña nueva'
        self.fields['new_password1'].help_text = 'Mínimo 8 caracteres, que no sean solo números ni se parezcan a tus datos.'
        self.fields['old_password'].widget.attrs.pop('autofocus', None)
        self.aplicar_estilos()


# Pide la contraseña antes de eliminar la cuenta.
class EliminarCuentaForm(EstiloFormularioMixin, forms.Form):
    password = forms.CharField(label='Confirma con tu contraseña', widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}))

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)
        self.aplicar_estilos()

    def clean_password(self):
        valor = self.cleaned_data['password']
        if self.usuario is None or not self.usuario.check_password(valor):
            raise forms.ValidationError('La contraseña no es correcta.')
        return valor


# Agrega un token oculto que evita registrar dos veces la misma solicitud (RNF03).
class TokenEnvioMixin:
    def configurar_token(self):
        self.fields['token_envio'] = forms.UUIDField(widget=forms.HiddenInput, required=False, initial=uuid.uuid4)


# Permite indicar el servicio del catálogo desde el que se llegó al formulario.
class ServicioOpcionalMixin:
    tipo_servicio = None

    def configurar_servicio(self):
        consulta = Servicio.objects.filter(activo=True)
        if self.tipo_servicio:
            consulta = consulta.filter(tipo=self.tipo_servicio)
        self.fields['servicio'] = forms.ModelChoiceField(queryset=consulta, required=False, widget=forms.HiddenInput)


# CU08 y CU09: formulario de cuatro pasos para crear una página web (DA-02).
# PASOS indica qué campos van en cada paso; la plantilla es solicitudes/crear_web.html.
class SolicitudWebForm(EstiloFormularioMixin, ServicioOpcionalMixin, TokenEnvioMixin, forms.Form):
    tipo_servicio = Servicio.TIPO_CREACION
    OPCIONES_SI_NO = [('no', 'No, es un proyecto nuevo'), ('si', 'Sí, ya tengo un sitio')]

    titulo = forms.CharField(label='Nombre del proyecto', max_length=200)
    tipo_sitio = forms.ChoiceField(label='Tipo de sitio', choices=RequerimientoWeb.TIPOS_SITIO, widget=forms.RadioSelect)
    tiene_sitio_actual = forms.ChoiceField(label='¿Tienes algún sitio web actualmente?', choices=OPCIONES_SI_NO, widget=forms.RadioSelect, initial='no')
    url_sitio_actual = forms.URLField(label='Dirección del sitio actual', required=False, assume_scheme='https', widget=CAMPO_URL)

    nombre_negocio = forms.CharField(label='Nombre de tu negocio', max_length=150)
    rubro = forms.ChoiceField(label='Giro o rubro', choices=[('', 'Selecciona una opción')] + RUBROS)
    descripcion_negocio = forms.CharField(label='Descripción del negocio', max_length=1000, widget=forms.Textarea(attrs={'rows': 4}))
    publico_objetivo = forms.CharField(label='¿A quién está dirigido?', max_length=200, required=False)
    objetivos = forms.MultipleChoiceField(label='¿Qué objetivos tiene tu página web?', choices=list(OBJETIVOS.items()), widget=forms.CheckboxSelectMultiple)

    funcionalidades = forms.MultipleChoiceField(label='Funcionalidades', choices=[(k, v['nombre']) for k, v in FUNCIONALIDADES.items()], widget=forms.CheckboxSelectMultiple, required=False)
    integraciones = forms.MultipleChoiceField(label='Integraciones', choices=[(k, v['nombre']) for k, v in INTEGRACIONES.items()], widget=forms.CheckboxSelectMultiple, required=False)
    num_paginas = forms.IntegerField(label='Cantidad aproximada de páginas', min_value=1, max_value=MAXIMO_PAGINAS, initial=5)
    complejidad = forms.ChoiceField(label='Nivel de diseño', choices=RequerimientoWeb.COMPLEJIDADES, widget=forms.RadioSelect, initial='media')
    estilo_visual = forms.ChoiceField(label='Estilo visual que prefieres', choices=RequerimientoWeb.ESTILOS, widget=forms.RadioSelect, required=False, initial='sin_preferencia')
    colores = forms.CharField(label='Colores de tu marca o que te gustan', max_length=120, required=False)
    secciones = forms.MultipleChoiceField(label='Secciones que quieres en tu sitio', choices=RequerimientoWeb.SECCIONES, widget=forms.CheckboxSelectMultiple, required=False)
    situacion_logo = forms.ChoiceField(label='¿Tienes logo?', choices=RequerimientoWeb.OPCIONES_LOGO, widget=forms.RadioSelect, required=False, initial='tiene')
    tiene_contenido = forms.BooleanField(label='Ya cuento con textos e imágenes para el sitio', required=False)
    sitios_referencia = forms.CharField(label='Sitios web que te gustan como referencia', max_length=1000, required=False, widget=forms.Textarea(attrs={'rows': 3}))
    dominio = forms.CharField(label='Dominio que tienes o quieres usar', max_length=120, required=False)
    presupuesto = forms.ChoiceField(label='Presupuesto aproximado', choices=RequerimientoWeb.PRESUPUESTOS, required=False, initial='por_definir')
    fecha_deseada = forms.DateField(label='Fecha deseada de entrega', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    medio_contacto = forms.ChoiceField(label='¿Cómo prefieres que te contactemos?', choices=RequerimientoWeb.MEDIOS_CONTACTO, widget=forms.RadioSelect, required=False, initial='correo')
    observaciones = forms.CharField(label='Comentarios adicionales', max_length=2000, required=False, widget=forms.Textarea(attrs={'rows': 3}))

    PASOS = {
        1: ['titulo', 'tipo_sitio', 'tiene_sitio_actual', 'url_sitio_actual'],
        2: ['nombre_negocio', 'rubro', 'descripcion_negocio', 'publico_objetivo', 'objetivos'],
        3: ['funcionalidades', 'integraciones', 'num_paginas', 'complejidad'],
        4: ['estilo_visual', 'colores', 'secciones', 'situacion_logo', 'tiene_contenido', 'sitios_referencia', 'dominio',
            'presupuesto', 'fecha_deseada', 'medio_contacto', 'observaciones'],
    }
    VALORES_POR_DEFECTO = {
        'estilo_visual': 'sin_preferencia',
        'situacion_logo': 'tiene',
        'presupuesto': 'por_definir',
        'medio_contacto': 'correo',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configurar_servicio()
        self.configurar_token()
        self.aplicar_estilos()
        self.fields['objetivos'].error_messages['required'] = 'Selecciona al menos un objetivo.'
        self.fields['tipo_sitio'].error_messages['required'] = 'Selecciona el tipo de sitio.'
        self.fields['titulo'].widget.attrs['placeholder'] = 'Ej: Sitio web para mi cafetería'
        self.fields['nombre_negocio'].widget.attrs['placeholder'] = 'Ej: Cafetería Aroma'
        self.fields['descripcion_negocio'].widget.attrs['placeholder'] = 'Qué hace tu negocio, qué ofrece y qué lo hace especial.'
        self.fields['publico_objetivo'].widget.attrs['placeholder'] = 'Ej: familias y estudiantes de Concepción'
        self.fields['colores'].widget.attrs['placeholder'] = 'Ej: azul marino y dorado'
        self.fields['sitios_referencia'].widget.attrs['placeholder'] = 'Pega las direcciones, una por línea'
        self.fields['dominio'].widget.attrs['placeholder'] = 'Ej: micafeteria.cl'
        self.fields['fecha_deseada'].widget.attrs['min'] = timezone.localdate().isoformat()
        self.fields['url_sitio_actual'].widget.attrs.update({
            'data-requerido-si': '#id_tiene_sitio_actual_1',
            'data-mensaje-requerido': 'Indica la dirección de tu sitio actual.',
        })

    # Rellena el formulario con lo que el cliente eligió en el estimador de la portada.
    @classmethod
    def inicial_desde_parametros(cls, parametros):
        inicial = {}
        tipos = dict(RequerimientoWeb.TIPOS_SITIO)
        if parametros.get('tipo_sitio') in tipos:
            inicial['tipo_sitio'] = parametros['tipo_sitio']
        if parametros.get('complejidad') in dict(RequerimientoWeb.COMPLEJIDADES):
            inicial['complejidad'] = parametros['complejidad']
        if parametros.get('rubro') in dict(RUBROS):
            inicial['rubro'] = parametros['rubro']
        paginas = parametros.get('num_paginas', '')
        if paginas.isdigit() and 1 <= int(paginas) <= MAXIMO_PAGINAS:
            inicial['num_paginas'] = int(paginas)
        funcionalidades = [c for c in parametros.getlist('funcionalidades') if c in FUNCIONALIDADES]
        if funcionalidades:
            inicial['funcionalidades'] = funcionalidades
        integraciones = [c for c in parametros.getlist('integraciones') if c in INTEGRACIONES]
        if integraciones:
            inicial['integraciones'] = integraciones
        return inicial

    def clean_fecha_deseada(self):
        return validar_fecha_futura(self.cleaned_data.get('fecha_deseada'))

    # Deja el dominio limpio (sin https:// ni www) y revisa que tenga un formato válido.
    def clean_dominio(self):
        dominio = self.cleaned_data.get('dominio', '').strip().lower()
        dominio = re.sub(r'^https?://', '', dominio).removeprefix('www.').rstrip('/')
        if dominio and not re.fullmatch(r'[a-z0-9áéíóúñ-]+(\.[a-z0-9-]+)+', dominio):
            raise forms.ValidationError('Escribe un dominio válido, por ejemplo micafeteria.cl.')
        return dominio

    # Completa los valores por defecto del paso 4 y exige la dirección si dijo que ya tiene sitio.
    def clean(self):
        datos = super().clean()
        for campo, valor in self.VALORES_POR_DEFECTO.items():
            if not datos.get(campo):
                datos[campo] = valor
        if datos.get('tiene_sitio_actual') == 'si' and not datos.get('url_sitio_actual'):
            self.add_error('url_sitio_actual', 'Indica la dirección de tu sitio actual.')
        if datos.get('tiene_sitio_actual') == 'no':
            datos['url_sitio_actual'] = ''
        return datos

    # Devuelve en qué paso está un campo.
    def paso_de(self, nombre_campo):
        for paso, campos in self.PASOS.items():
            if nombre_campo in campos:
                return paso
        return 1

    # Paso que se abre cuando hay errores, para mostrarle al cliente qué corregir.
    @property
    def primer_paso_con_error(self):
        if not self.errors:
            return 1
        return min(self.paso_de(campo) for campo in self.errors)


# Base de los formularios de mejora, soporte y mantenimiento (CU08 con CU10 Adjuntar archivos).
class SolicitudSimpleForm(EstiloFormularioMixin, ServicioOpcionalMixin, TokenEnvioMixin, forms.Form):
    def __init__(self, *args, cliente=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.configurar_servicio()
        self.configurar_token()
        consulta = Solicitud.objects.none()
        if cliente is not None and cliente.is_authenticated:
            consulta = Solicitud.objects.filter(cliente=cliente).order_by('-fecha_solicitud')
        self.fields['relacionada'] = forms.ModelChoiceField(
            label='¿Tiene relación con una solicitud anterior?',
            queryset=consulta,
            required=False,
            empty_label='No, es un tema nuevo',
        )
        self.fields['relacionada'].label_from_instance = lambda s: f'{s.numero}: {s.titulo}'
        self.fields['adjunto'] = forms.FileField(
            label='Archivo adjunto',
            required=False,
            help_text=texto_ayuda_adjuntos(),
            validators=[validar_archivo],
        )
        self.aplicar_estilos()
        if not consulta.exists():
            self.fields['relacionada'].widget = forms.HiddenInput()


# Solicitud de mejora de un sitio existente.
class SolicitudMejoraForm(SolicitudSimpleForm):
    tipo_servicio = Servicio.TIPO_MEJORA
    TIPOS_MEJORA = [
        ('rediseno', 'Rediseño visual'),
        ('responsive', 'Adaptación a celulares'),
        ('velocidad', 'Mejorar velocidad de carga'),
        ('seo', 'Posicionamiento en buscadores (SEO)'),
        ('secciones', 'Nuevas secciones o páginas'),
        ('funciones', 'Nuevas funcionalidades'),
        ('otro', 'Otro'),
    ]

    titulo = forms.CharField(label='Título de la solicitud', max_length=200)
    url_sitio = forms.URLField(label='Dirección de tu sitio', assume_scheme='https', widget=CAMPO_URL)
    tipos_mejora = forms.MultipleChoiceField(label='¿Qué quieres mejorar?', choices=TIPOS_MEJORA, widget=forms.CheckboxSelectMultiple)
    descripcion = forms.CharField(label='Describe los cambios', max_length=3000, widget=forms.Textarea(attrs={'rows': 5}))
    fecha_deseada = forms.DateField(label='Fecha deseada', required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipos_mejora'].error_messages['required'] = 'Selecciona al menos un tipo de mejora.'
        self.fields['titulo'].widget.attrs['placeholder'] = 'Ej: Rediseño de la página de inicio'
        self.fields['descripcion'].widget.attrs['placeholder'] = 'Qué te gustaría cambiar, qué no funciona hoy y ejemplos de sitios que te gusten.'
        self.fields['fecha_deseada'].widget.attrs['min'] = timezone.localdate().isoformat()

    def clean_fecha_deseada(self):
        return validar_fecha_futura(self.cleaned_data.get('fecha_deseada'))


# Solicitud de soporte técnico por una falla.
class SolicitudSoporteForm(SolicitudSimpleForm):
    tipo_servicio = Servicio.TIPO_SOPORTE
    TIPOS_PROBLEMA = [
        ('caido', 'El sitio no carga o está caído'),
        ('errores', 'Errores o funciones que no responden'),
        ('seguridad', 'Problema de seguridad o sitio vulnerado'),
        ('lentitud', 'El sitio está muy lento'),
        ('correo', 'Problemas con correos o formularios'),
        ('otro', 'Otro'),
    ]

    titulo = forms.CharField(label='Resumen del problema', max_length=200)
    url_sitio = forms.URLField(label='Dirección del sitio afectado', assume_scheme='https', widget=CAMPO_URL)
    tipo_problema = forms.ChoiceField(label='Tipo de problema', choices=TIPOS_PROBLEMA)
    desde_cuando = forms.CharField(label='¿Desde cuándo ocurre?', max_length=100, required=False)
    prioridad = forms.ChoiceField(label='Prioridad', choices=Solicitud.PRIORIDADES, initial='media')
    descripcion = forms.CharField(label='Describe lo que ocurre', max_length=3000, widget=forms.Textarea(attrs={'rows': 5}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['titulo'].widget.attrs['placeholder'] = 'Ej: El formulario de contacto no envía mensajes'
        self.fields['desde_cuando'].widget.attrs['placeholder'] = 'Ej: desde ayer en la tarde'
        self.fields['descripcion'].widget.attrs['placeholder'] = 'Pasos para reproducir el problema, mensajes de error y cambios recientes.'


# Solicitud de mantenimiento periódico.
class SolicitudMantenimientoForm(SolicitudSimpleForm):
    tipo_servicio = Servicio.TIPO_MANTENIMIENTO
    PLATAFORMAS = [
        ('wordpress', 'WordPress'),
        ('woocommerce', 'WooCommerce'),
        ('shopify', 'Shopify'),
        ('medida', 'Desarrollo a medida'),
        ('nose', 'No lo sé'),
    ]
    FRECUENCIAS = [('mensual', 'Mensual'), ('trimestral', 'Trimestral')]
    TAREAS = [
        ('respaldos', 'Respaldos periódicos'),
        ('actualizaciones', 'Actualizaciones de seguridad'),
        ('monitoreo', 'Monitoreo de disponibilidad'),
        ('contenido', 'Cambios menores de contenido'),
        ('informe', 'Informe mensual de estado'),
    ]

    titulo = forms.CharField(label='Título de la solicitud', max_length=200)
    url_sitio = forms.URLField(label='Dirección del sitio', assume_scheme='https', widget=CAMPO_URL)
    plataforma = forms.ChoiceField(label='¿Con qué está construido?', choices=PLATAFORMAS)
    frecuencia = forms.ChoiceField(label='Frecuencia', choices=FRECUENCIAS, widget=forms.RadioSelect, initial='mensual')
    tareas = forms.MultipleChoiceField(label='Tareas que necesitas', choices=TAREAS, widget=forms.CheckboxSelectMultiple)
    descripcion = forms.CharField(label='Información adicional', max_length=3000, required=False, widget=forms.Textarea(attrs={'rows': 4}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tareas'].error_messages['required'] = 'Selecciona al menos una tarea.'
        self.fields['titulo'].widget.attrs['placeholder'] = 'Ej: Plan de mantenimiento para tienda online'


# CU13 Conversar con el equipo.
class MensajeForm(EstiloFormularioMixin, forms.Form):
    texto = forms.CharField(label='Mensaje', max_length=3000, widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos()
        self.fields['texto'].widget.attrs['placeholder'] = 'Escribe tu mensaje'

    def clean_texto(self):
        texto = self.cleaned_data['texto'].strip()
        if not texto:
            raise forms.ValidationError('Escribe un mensaje.')
        return texto


# CU10 Adjuntar archivos a una solicitud ya creada.
class AdjuntoForm(EstiloFormularioMixin, forms.Form):
    archivo = forms.FileField(label='Archivo', validators=[validar_archivo])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['archivo'].help_text = texto_ayuda_adjuntos().replace('Opcional. ', '')
        self.aplicar_estilos()


# CU17 Actualizar estado: solo ofrece las transiciones permitidas.
class CambioEstadoForm(EstiloFormularioMixin, forms.Form):
    estado = forms.ModelChoiceField(label='Nuevo estado', queryset=EstadoSolicitud.objects.all(), empty_label=None)
    comentario = forms.CharField(label='Comentario para el cliente', required=False, max_length=1000, widget=forms.Textarea(attrs={'rows': 3}))
    notificar = forms.BooleanField(label='Avisar al cliente por correo', required=False, initial=True)

    def __init__(self, *args, solicitud=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.solicitud = solicitud
        if solicitud is not None:
            self.fields['estado'].initial = solicitud.estado_id
        self.aplicar_estilos()

    def clean_estado(self):
        from .gestion import validar_transicion

        estado = self.cleaned_data['estado']
        if self.solicitud is not None:
            error = validar_transicion(self.solicitud, estado)
            if error:
                raise forms.ValidationError(error)
        return estado


# CU16 Emitir cotización definitiva: plazo, vigencia y alcance.
class CotizacionForm(EstiloFormularioMixin, forms.ModelForm):
    class Meta:
        model = Cotizacion
        fields = ['plazo_dias', 'validez_dias', 'detalle']
        widgets = {'detalle': forms.Textarea(attrs={'rows': 4})}
        labels = {'detalle': 'Alcance y condiciones'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos()
        self.fields['plazo_dias'].widget.attrs['min'] = 1
        self.fields['validez_dias'].widget.attrs['min'] = 1

    def clean_plazo_dias(self):
        valor = self.cleaned_data['plazo_dias']
        if valor < 1:
            raise forms.ValidationError('El plazo debe ser de al menos 1 día.')
        return valor

    def clean_validez_dias(self):
        valor = self.cleaned_data['validez_dias']
        if valor < 1:
            raise forms.ValidationError('La vigencia debe ser de al menos 1 día.')
        return valor


# Un ítem de la cotización (descripción, cantidad y precio unitario).
class ItemCotizacionForm(EstiloFormularioMixin, forms.Form):
    descripcion = forms.CharField(label='Descripción', max_length=200)
    cantidad = forms.IntegerField(label='Cantidad', min_value=1, max_value=999, initial=1)
    precio_unitario = forms.IntegerField(label='Precio unitario', min_value=0, max_value=999999999)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos()
        self.fields['cantidad'].widget.attrs.update({'min': 1, 'inputmode': 'numeric'})
        self.fields['precio_unitario'].widget.attrs.update({'min': 0, 'step': 1000, 'inputmode': 'numeric'})


# Conjunto de ítems; valida que haya al menos uno y calcula el monto neto.
class BaseItemsCotizacionFormSet(forms.BaseFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        items = self.items()
        if not items:
            raise forms.ValidationError('Agrega al menos un ítem a la cotización.')
        if sum(item['subtotal'] for item in items) < 1000:
            raise forms.ValidationError('El monto total de la cotización debe ser de al menos $1.000.')

    def items(self):
        resultado = []
        for formulario in self.forms:
            datos = getattr(formulario, 'cleaned_data', None) or {}
            if not datos or datos.get('DELETE') or not datos.get('descripcion'):
                continue
            cantidad = datos.get('cantidad') or 1
            precio = datos.get('precio_unitario') or 0
            resultado.append({
                'descripcion': datos['descripcion'].strip(),
                'cantidad': cantidad,
                'precio_unitario': precio,
                'subtotal': cantidad * precio,
            })
        return resultado


ItemsCotizacionFormSet = formset_factory(
    ItemCotizacionForm,
    formset=BaseItemsCotizacionFormSet,
    extra=0,
    can_delete=True,
    max_num=40,
    validate_max=True,
)


# Datos internos del equipo: responsable, prioridad y notas.
class GestionInternaForm(EstiloFormularioMixin, forms.ModelForm):
    class Meta:
        model = Solicitud
        fields = ['responsable', 'prioridad', 'notas_internas']
        widgets = {'notas_internas': forms.Textarea(attrs={'rows': 4})}
        labels = {'notas_internas': 'Notas internas (no visibles para el cliente)'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsable'].queryset = User.objects.filter(is_staff=True, is_active=True).order_by('first_name', 'email')
        self.fields['responsable'].empty_label = 'Sin asignar'
        self.fields['responsable'].label_from_instance = lambda u: u.get_full_name() or u.email
        self.aplicar_estilos()


# CU12 Responder cotización: aceptar o rechazar con comentario.
class RespuestaCotizacionForm(EstiloFormularioMixin, forms.Form):
    respuesta = forms.ChoiceField(choices=[('aceptada', 'Aceptar'), ('rechazada', 'Rechazar')])
    comentario = forms.CharField(label='Comentario (opcional)', required=False, max_length=1000, widget=forms.Textarea(attrs={'rows': 2}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos()


# CU18 Gestionar servicios.
class ServicioForm(EstiloFormularioMixin, forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['nombre', 'tipo', 'categoria', 'resumen', 'descripcion', 'incluye', 'precio_base', 'plazo_referencial', 'destacado', 'activo']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4}),
            'incluye': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {'precio_base': 'Precio desde (CLP)', 'plazo_referencial': 'Plazo referencial', 'destacado': 'Mostrar en la página de inicio'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].queryset = Categoria.objects.all()
        self.aplicar_estilos()


# CU18 Gestionar categorías.
class CategoriaForm(EstiloFormularioMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion', 'icono', 'orden', 'activa']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3})}
        help_texts = {'icono': 'Clase de Font Awesome, por ejemplo: fa-solid fa-code'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos()

    def clean_icono(self):
        icono = self.cleaned_data['icono'].strip()
        if not re.fullmatch(r'fa-(solid|regular|brands) fa-[a-z0-9-]+', icono):
            raise forms.ValidationError('Usa el formato "fa-solid fa-nombre", por ejemplo: fa-solid fa-code.')
        return icono


# CU19 Gestionar contenido: preguntas frecuentes.
class PreguntaFrecuenteForm(EstiloFormularioMixin, forms.ModelForm):
    class Meta:
        model = PreguntaFrecuente
        fields = ['pregunta', 'respuesta', 'palabras_clave', 'orden', 'activa']
        widgets = {'respuesta': forms.Textarea(attrs={'rows': 4})}
        labels = {'activa': 'Mostrar en el sitio y usar en el asistente'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos()


# CU19 Gestionar contenido: datos de contacto y aviso del sitio.
class ConfiguracionSitioForm(EstiloFormularioMixin, forms.ModelForm):
    class Meta:
        model = ConfiguracionSitio
        fields = ['correo_contacto', 'whatsapp', 'whatsapp_visible', 'ubicacion', 'horario', 'aviso']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos()
        self.fields['whatsapp'].widget.attrs['inputmode'] = 'numeric'

    def clean_whatsapp(self):
        valor = re.sub(r'\D', '', self.cleaned_data['whatsapp'])
        if len(valor) < 8 or len(valor) > 15:
            raise forms.ValidationError('Ingresa el número con código de país, solo dígitos. Ejemplo: 56912345678')
        return valor
