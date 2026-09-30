# AXZTRA · Plataforma web de servicios de desarrollo web

Plataforma web para la gestión de servicios de creación, mejora, soporte técnico y mantenimiento de páginas web. Permite a los clientes describir sus requerimientos mediante un formulario guiado, obtener una estimación referencial inmediata y seguir el avance de cada solicitud; y al equipo AXZTRA administrar solicitudes, cotizaciones, servicios y clientes desde un panel protegido con verificación en dos pasos.

Proyecto desarrollado para la asignatura Taller de Sistemas de Información II, Universidad Técnica Federico Santa María.

Equipo: Benjamín Ruiz, Camilo Barra y Franco Constanzo.

## Funcionalidades

| Requisito | Implementación |
|-----------|----------------|
| RF01 Registro e inicio de sesión | Registro con correo, inicio de sesión por correo, recuperación de contraseña por correo y edición de datos personales. |
| RF02 Catálogo de servicios | Catálogo con búsqueda y filtros por tipo y categoría, más ficha de detalle por servicio. |
| RF03 Selección del tipo de servicio | Selector de los cuatro servicios: creación, mejora, soporte y mantenimiento. |
| RF04 Formulario guiado | Formulario de tres pasos (información básica, negocio y funcionalidades) con validación por paso. |
| RF05 Estimación automática | Cálculo por reglas: precio base según tipo de sitio + funcionalidades e integraciones × factor de complejidad, con rango de precio y plazo. |
| RF06 Registro de solicitudes | Cada solicitud recibe un número correlativo (AXZ-AAMM-0001) y queda asociada al cliente. |
| RF07 Seguimiento | Línea de avance por estado, historial de cambios, estimación y cotización formal visibles para el cliente. |
| RF08 Gestión administrativa | Panel con métricas, filtros, cambio de estado, emisión de cotizaciones, prioridad y notas internas. |
| RF09 Gestión de servicios | Alta, edición y activación de servicios y categorías desde el panel. |
| RF10 Asistente virtual | Asistente flotante disponible en todo el sitio, con historial por usuario o sesión. |
| RF11 Notificaciones | Correos al registrar una solicitud, cambiar su estado, emitir o responder una cotización y cancelar. |
| RF12 Respuesta a cotizaciones | El cliente acepta o rechaza la cotización formal dentro de su vigencia. |
| RNF04 Seguridad | Acceso al panel y a la administración de Django con código de verificación de 6 dígitos enviado por correo. |

### Asistente virtual

El asistente responde con reglas de intención definidas en `plataforma/asistente.py` (servicios, precios, plazos, soporte, seguimiento, cuenta y contacto) y ofrece accesos directos a los formularios. La clase `AsistenteVirtual` expone el método `responder(mensaje)`, que es el punto de integración previsto para conectar un motor conversacional externo como Botpress sin modificar las vistas ni la interfaz.

## Tecnologías

- Python 3.12 y Django 5.0
- SQLite en desarrollo; PostgreSQL mediante variables de entorno
- Bootstrap 5, Font Awesome y JavaScript sin dependencias adicionales

## Estructura

```
axztra/                 Configuración del proyecto (settings, urls, wsgi, asgi)
plataforma/
    models.py           Modelo de datos
    forms.py            Formularios y validaciones
    estimacion.py       Reglas de cálculo de la estimación
    gestion.py          Operaciones de negocio sobre solicitudes
    notificaciones.py   Envío de correos
    verificacion.py     Verificación en dos pasos
    asistente.py        Asistente virtual
    views/              Vistas públicas, de cuenta, de cliente, del panel y del asistente
    templates/          Plantillas HTML y de correo
    static/             Estilos, scripts e imágenes
    migrations/         Esquema de base de datos y datos iniciales
    management/         Comando datos_demo
    tests.py            Pruebas automatizadas
```

## Instalación

Los pasos detallados para Windows y Visual Studio Code están en `INSTRUCCIONES.txt`. En resumen:

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py datos_demo
python manage.py runserver
```

Luego abrir http://127.0.0.1:8000

## Cuentas de demostración

El comando `python manage.py datos_demo` crea:

| Rol | Correo | Contraseña |
|-----|--------|------------|
| Administrador | admin@axztra.cl | AxztraAdmin2026 |
| Cliente | cliente@axztra.cl | Cliente2026 |

Al ingresar como administrador se solicita un código de verificación. En desarrollo los correos no se envían: se muestran en la terminal donde se ejecuta el servidor.

## Rutas principales

| Ruta | Descripción |
|------|-------------|
| `/` | Página de inicio |
| `/servicios/` | Catálogo de servicios |
| `/solicitudes/nueva/` | Nueva solicitud |
| `/solicitudes/` | Mis solicitudes |
| `/panel/` | Panel de administración |
| `/admin/` | Administración de datos de Django |

## Configuración

Variables de entorno opcionales:

| Variable | Uso |
|----------|-----|
| `DJANGO_SECRET_KEY` | Clave secreta en producción |
| `DJANGO_DEBUG` | `False` en producción |
| `DJANGO_ALLOWED_HOSTS` | Dominios permitidos, separados por coma |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` | Conexión a PostgreSQL (requiere instalar `psycopg`) |
| `DJANGO_EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Envío real de correos por SMTP |
| `AXZTRA_WHATSAPP`, `AXZTRA_WHATSAPP_VISIBLE`, `AXZTRA_CORREO`, `AXZTRA_CORREO_ADMIN` | Datos de contacto de la empresa |

## Pruebas

```
python manage.py test
```

La batería cubre el cálculo de la estimación, registro e inicio de sesión, verificación en dos pasos, el flujo completo de solicitudes, permisos entre clientes, cambios de estado, cotizaciones, el panel y el asistente.
