import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

from .estimacion import FUNCIONALIDADES, INTEGRACIONES, MAXIMO_PAGINAS, OBJETIVOS, RUBROS
from .models import Categoria, Cotizacion, EstadoSolicitud, PerfilCliente, RequerimientoWeb, Servicio, Solicitud

User = get_user_model()

CAMPO_URL = forms.TextInput(attrs={'inputmode': 'url', 'autocomplete': 'url'})


class EstiloBootstrapMixin:
    def aplicar_estilos(self):
        for campo in self.fields.values():
            widget = campo.widget
            if isinstance(widget, (forms.CheckboxSelectMultiple, forms.RadioSelect)):
                continue
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', 'form-select')
            else:
                widget.attrs.setdefault('class', 'form-control')


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


def validar_telefono(valor):
    valor = (valor or '').strip()
    if not valor:
        return ''
    digitos = re.sub(r'\D', '', valor)
    if len(digitos) < 8 or len(digitos) > 12:
        raise forms.ValidationError('Ingresa un teléfono válido, por ejemplo +56 9 1234 5678.')
    return valor


def validar_fecha_futura(fecha):
    if fecha and fecha < timezone.localdate():
        raise forms.ValidationError('La fecha deseada no puede estar en el pasado.')
    return fecha


class RegistroForm(EstiloBootstrapMixin, UserCreationForm):
    first_name = forms.CharField(label='Nombre', max_length=80)
    last_name = forms.CharField(label='Apellido', max_length=80)
    email = forms.EmailField(label='Correo electrónico')
    empresa = forms.CharField(label='Empresa o emprendimiento', max_length=200, required=False)
    telefono = forms.CharField(label='Teléfono', max_length=20, required=False)
    acepta_terminos = forms.BooleanField(
        label='Acepto que AXZTRA use mis datos para gestionar mis solicitudes',
        error_messages={'required': 'Debes aceptar el uso de tus datos para crear la cuenta.'},
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = 'Contraseña'
        self.fields['password2'].label = 'Repite la contraseña'
        self.fields['password1'].help_text = 'Mínimo 8 caracteres, no solo números y distinta de tus datos personales.'
        self.fields['password2'].help_text = ''
        self.aplicar_estilos()
        self.fields['email'].widget.attrs.update({'autocomplete': 'email', 'placeholder': 'nombre@correo.cl'})
        self.fields['telefono'].widget.attrs.update({'placeholder': '+56 9 1234 5678'})

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este correo. Inicia sesión o recupera tu contraseña.')
        return email

    def clean_telefono(self):
        return validar_telefono(self.cleaned_data.get('telefono'))

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
                },
            )
        return usuario


class LoginForm(EstiloBootstrapMixin, forms.Form):
    email = forms.EmailField(label='Correo electrónico')
    password = forms.CharField(label='Contraseña', widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos()
        self.fields['email'].widget.attrs.update({'autocomplete': 'email', 'placeholder': 'nombre@correo.cl', 'autofocus': True})
        self.fields['password'].widget.attrs.update({'autocomplete': 'current-password'})

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()


class CodigoVerificacionForm(EstiloBootstrapMixin, forms.Form):
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
            'class': 'form-control codigo-input',
            'autofocus': True,
        })


class CuentaForm(EstiloBootstrapMixin, forms.ModelForm):
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
        self.fields = {nombre: self.fields[nombre] for nombre in ['first_name', 'last_name', 'empresa', 'rut', 'telefono', 'ciudad', 'recibir_notificaciones']}
        self.aplicar_estilos()
        self.fields['rut'].widget.attrs['placeholder'] = '12.345.678-9'

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


class ServicioOpcionalMixin:
    tipo_servicio = None

    def configurar_servicio(self):
        consulta = Servicio.objects.filter(activo=True)
        if self.tipo_servicio:
            consulta = consulta.filter(tipo=self.tipo_servicio)
        self.fields['servicio'] = forms.ModelChoiceField(queryset=consulta, required=False, widget=forms.HiddenInput)


class SolicitudWebForm(EstiloBootstrapMixin, ServicioOpcionalMixin, forms.Form):
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
    tiene_contenido = forms.BooleanField(label='Ya cuento con textos, logo e imágenes para el sitio', required=False)
    fecha_deseada = forms.DateField(label='Fecha deseada de entrega', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    observaciones = forms.CharField(label='Comentarios adicionales', max_length=2000, required=False, widget=forms.Textarea(attrs={'rows': 3}))

    PASOS = {
        1: ['titulo', 'tipo_sitio', 'tiene_sitio_actual', 'url_sitio_actual'],
        2: ['nombre_negocio', 'rubro', 'descripcion_negocio', 'publico_objetivo', 'objetivos'],
        3: ['funcionalidades', 'integraciones', 'num_paginas', 'complejidad', 'tiene_contenido', 'fecha_deseada', 'observaciones'],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configurar_servicio()
        self.aplicar_estilos()
        self.fields['objetivos'].error_messages['required'] = 'Selecciona al menos un objetivo.'
        self.fields['titulo'].widget.attrs['placeholder'] = 'Ej: Sitio web para mi cafetería'
        self.fields['nombre_negocio'].widget.attrs['placeholder'] = 'Ej: Cafetería Aroma'
        self.fields['descripcion_negocio'].widget.attrs['placeholder'] = 'Qué hace tu negocio, qué productos o servicios ofrece y qué lo hace especial.'
        self.fields['publico_objetivo'].widget.attrs['placeholder'] = 'Ej: familias y estudiantes de Concepción'
        self.fields['url_sitio_actual'].widget.attrs['placeholder'] = 'https://www.tusitio.cl'

    def clean_fecha_deseada(self):
        return validar_fecha_futura(self.cleaned_data.get('fecha_deseada'))

    def clean(self):
        datos = super().clean()
        if datos.get('tiene_sitio_actual') == 'si' and not datos.get('url_sitio_actual'):
            self.add_error('url_sitio_actual', 'Indica la dirección de tu sitio actual.')
        if datos.get('tiene_sitio_actual') == 'no':
            datos['url_sitio_actual'] = ''
        return datos

    def paso_de(self, nombre_campo):
        for paso, campos in self.PASOS.items():
            if nombre_campo in campos:
                return paso
        return 1

    @property
    def primer_paso_con_error(self):
        if not self.errors:
            return 1
        return min(self.paso_de(campo) for campo in self.errors)


class SolicitudMejoraForm(EstiloBootstrapMixin, ServicioOpcionalMixin, forms.Form):
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
        self.configurar_servicio()
        self.aplicar_estilos()
        self.fields['tipos_mejora'].error_messages['required'] = 'Selecciona al menos un tipo de mejora.'
        self.fields['titulo'].widget.attrs['placeholder'] = 'Ej: Rediseño de la página de inicio'
        self.fields['url_sitio'].widget.attrs['placeholder'] = 'https://www.tusitio.cl'
        self.fields['descripcion'].widget.attrs['placeholder'] = 'Qué te gustaría cambiar, qué no te funciona hoy y ejemplos de sitios que te gusten.'

    def clean_fecha_deseada(self):
        return validar_fecha_futura(self.cleaned_data.get('fecha_deseada'))


class SolicitudSoporteForm(EstiloBootstrapMixin, ServicioOpcionalMixin, forms.Form):
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
        self.configurar_servicio()
        self.aplicar_estilos()
        self.fields['titulo'].widget.attrs['placeholder'] = 'Ej: El formulario de contacto no envía mensajes'
        self.fields['url_sitio'].widget.attrs['placeholder'] = 'https://www.tusitio.cl'
        self.fields['desde_cuando'].widget.attrs['placeholder'] = 'Ej: desde ayer en la tarde'
        self.fields['descripcion'].widget.attrs['placeholder'] = 'Pasos para reproducir el problema, mensajes de error y cualquier cambio reciente.'


class SolicitudMantenimientoForm(EstiloBootstrapMixin, ServicioOpcionalMixin, forms.Form):
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
        self.configurar_servicio()
        self.aplicar_estilos()
        self.fields['tareas'].error_messages['required'] = 'Selecciona al menos una tarea.'
        self.fields['titulo'].widget.attrs['placeholder'] = 'Ej: Plan de mantenimiento para tienda online'
        self.fields['url_sitio'].widget.attrs['placeholder'] = 'https://www.tusitio.cl'


class CambioEstadoForm(EstiloBootstrapMixin, forms.Form):
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
        estado = self.cleaned_data['estado']
        if self.solicitud is not None and estado.pk == self.solicitud.estado_id:
            raise forms.ValidationError('La solicitud ya se encuentra en ese estado.')
        if estado.codigo == EstadoSolicitud.COTIZADA and not hasattr(self.solicitud, 'cotizacion'):
            raise forms.ValidationError('Primero emite la cotización definitiva.')
        return estado


class CotizacionForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Cotizacion
        fields = ['monto', 'plazo_dias', 'validez_dias', 'detalle']
        widgets = {'detalle': forms.Textarea(attrs={'rows': 5})}
        help_texts = {'monto': 'Valor en pesos chilenos, sin IVA.'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos()
        self.fields['monto'].widget.attrs['min'] = 1
        self.fields['plazo_dias'].widget.attrs['min'] = 1
        self.fields['validez_dias'].widget.attrs['min'] = 1

    def clean_monto(self):
        monto = self.cleaned_data['monto']
        if monto < 1000:
            raise forms.ValidationError('Ingresa un monto válido en pesos.')
        return monto

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


class GestionInternaForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Solicitud
        fields = ['prioridad', 'notas_internas']
        widgets = {'notas_internas': forms.Textarea(attrs={'rows': 4})}
        labels = {'notas_internas': 'Notas internas (no visibles para el cliente)'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos()


class RespuestaCotizacionForm(EstiloBootstrapMixin, forms.Form):
    respuesta = forms.ChoiceField(choices=[('aceptada', 'Aceptar'), ('rechazada', 'Rechazar')])
    comentario = forms.CharField(label='Comentario (opcional)', required=False, max_length=1000, widget=forms.Textarea(attrs={'rows': 2}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos()


class ServicioForm(EstiloBootstrapMixin, forms.ModelForm):
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


class CategoriaForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion', 'icono', 'orden', 'activa']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3})}
        help_texts = {'icono': 'Clase de Font Awesome, por ejemplo: fa-solid fa-code'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos()
