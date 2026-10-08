# Guía del proyecto AXZTRA

Esta guía relaciona el Informe Final de Diseño con el código, para saber dónde está cada cosa.
Los nombres de casos de uso (CU), tablas, diagramas y requisitos son los mismos del informe.

## 1. Organización de carpetas

| Carpeta o archivo | Qué contiene |
|---|---|
| `manage.py` | Comandos de Django: `runserver`, `migrate`, `test`, `datos_demo`, etc. |
| `.env` y `.env.example` | Datos de conexión a PostgreSQL y opciones propias. Se copia `.env.example` como `.env` y se completa la clave. |
| `axztra/settings.py` | Configuración del proyecto (base de datos, correo, seguridad). |
| `axztra/urls.py` | Rutas principales: administración de datos, API y aplicación. |
| `plataforma/models.py` | Modelo de datos: una clase por tabla (secciones 4.1 a 4.3 del informe). |
| `plataforma/forms.py` | Formularios y sus validaciones. |
| `plataforma/gestion.py` | Reglas de negocio: crear solicitudes, cambiar estados, cotizar, mensajes y archivos. |
| `plataforma/estimacion.py` | Fórmula de estimación referencial (sección 3.5 y Tabla 11). |
| `plataforma/asistente.py` | Asistente virtual con reglas propias (CU03). |
| `plataforma/recomendaciones.py` | Sugerencias de funcionalidades según el rubro. |
| `plataforma/notificaciones.py` | Correos automáticos (CU21). |
| `plataforma/seguridad.py`, `verificacion.py`, `auditoria.py` | Seguridad, verificación en dos pasos y registro de actividad. |
| `plataforma/views/` | Pantallas: `publico.py`, `cuentas.py`, `cliente.py`, `panel.py` y `asistente.py`. |
| `plataforma/api/` | API REST para sistemas externos (CU22). |
| `plataforma/templates/plataforma/` | Plantillas HTML de cada pantalla. |
| `plataforma/templates/plataforma/correos/` | Textos de los correos automáticos. |
| `plataforma/static/css/` | Estilos: `base.css`, `animaciones.css`, `tema.css` y `adaptable.css`. |
| `plataforma/static/js/` | JavaScript: `app.js` (general), `estimador.js` (estimación y pasos) y `panel.js` (panel). |
| `plataforma/migrations/` | Cambios de la base de datos, en orden. |
| `plataforma/tests.py` | Pruebas automáticas. |

## 2. Casos de uso y dónde están

| Caso de uso | Dirección | Vista | Plantilla |
|---|---|---|---|
| CU01 Consultar catálogo de servicios | `/servicios/` y `/servicios/<slug>/` | `publico.catalogo`, `publico.servicio_detalle` | `catalogo.html`, `servicio_detalle.html` |
| CU02 Obtener estimación referencial | `/` (estimador) y `/solicitudes/nueva/web/estimacion/` | `publico.inicio`, `cliente.estimacion_web` | `inicio.html`, `solicitudes/estimacion.html` |
| CU03 Consultar asistente virtual | `/asistente/mensaje/` | `views/asistente.py` | `includes/asistente.html` (solo en pantallas de solicitud) |
| CU04 Registrarse | `/cuenta/registro/` | `cuentas.registro` | `auth/registro.html` |
| CU05 Iniciar sesión | `/cuenta/ingresar/` | `cuentas.login_view` | `auth/login.html` |
| CU06 Recuperar contraseña | `/cuenta/recuperar/` | `cuentas.RecuperarClaveView` | `auth/recuperar*.html` |
| CU07 Verificar código de acceso (clientes y equipo) | `/cuenta/verificacion/` | `cuentas.verificar_codigo` | `auth/verificar_codigo.html` |
| CU08 Solicitar servicio | `/solicitudes/nueva/` | `cliente.nueva_solicitud` y formularios de cada tipo | `solicitudes/nueva.html` |
| CU09 Levantar requerimientos | `/solicitudes/nueva/web/` | `cliente.crear_web` | `solicitudes/crear_web.html` (cuatro pasos) |
| CU10 Adjuntar archivos | `/solicitudes/<id>/archivos/` | `cliente.subir_adjunto` | `cliente/ver_solicitud.html` |
| CU11 Consultar mis solicitudes | `/solicitudes/` y `/solicitudes/<id>/` | `cliente.mis_solicitudes`, `cliente.ver_solicitud` | `cliente/mis_solicitudes.html`, `cliente/ver_solicitud.html` |
| CU12 Responder cotización | `/solicitudes/<id>/cotizacion/` | `cliente.responder_cotizacion` | `cliente/ver_solicitud.html` |
| CU13 Conversar con el equipo | `/solicitudes/<id>/mensajes/` | `cliente.enviar_mensaje` y ficha del panel | `cliente/ver_solicitud.html`, `panel/solicitud.html` |
| CU14 Gestionar mi cuenta | `/cuenta/` | `cuentas.mi_cuenta` | `cliente/mi_cuenta.html` |
| CU15 Gestionar solicitudes | `/panel/solicitudes/` | `panel.panel_solicitudes`, `panel.panel_solicitud` | `panel/solicitudes.html`, `panel/solicitud.html` |
| CU16 Emitir cotización definitiva | Ficha de la solicitud en el panel | `panel.panel_solicitud` | `panel/solicitud.html` |
| CU17 Actualizar estado | Ficha del panel y `/panel/tablero/` | `panel.panel_solicitud`, `panel.panel_mover_solicitud` | `panel/solicitud.html`, `panel/tablero.html` |
| CU18 Gestionar servicios y categorías | `/panel/servicios/` | `panel.panel_servicios` | `panel/servicios.html` |
| CU19 Gestionar contenido del sitio | `/panel/contenido/` | `panel.panel_contenido` | `panel/contenido.html` |
| CU20 Consultar indicadores y reportes | `/panel/` y `/panel/actividad/` | `panel.panel_inicio`, `panel.panel_actividad` | `panel/inicio.html`, `panel/actividad.html` |
| CU21 Notificar por correo | Automático | `notificaciones.py` | `correos/*.txt` |
| CU22 Consultar solicitudes vía API | `/api/v1/...` | `api/views.py` | Respuestas JSON |

## 3. Tablas del informe y modelos

| Tabla del informe | Tabla en la base | Clase en `models.py` |
|---|---|---|
| Tabla 13 | `auth_user` | Usuario (viene con Django) |
| Tabla 14 | `plataforma_perfilcliente` | `PerfilCliente` |
| Tabla 15 | `plataforma_categoria` | `Categoria` |
| Tabla 16 | `plataforma_servicio` | `Servicio` |
| Tabla 17 | `plataforma_estadosolicitud` | `EstadoSolicitud` |
| Tabla 18 | `plataforma_solicitud` | `Solicitud` |
| Tabla 19 | `plataforma_requerimientoweb` | `RequerimientoWeb` |
| Tabla 20 | `plataforma_estimacion` | `Estimacion` |
| Tabla 21 | `plataforma_cotizacion` | `Cotizacion` |
| Tabla 22 | `plataforma_historialsolicitud` | `HistorialSolicitud` |
| Tabla 23 | `plataforma_mensajesolicitud` | `MensajeSolicitud` |
| Tabla 24 | `plataforma_adjunto` | `Adjunto` |
| Tabla 25 | `plataforma_mensajeasistente` | `MensajeAsistente` |
| Tabla 26 | `plataforma_codigoverificacion` | `CodigoVerificacion` |
| Tabla 27 | `plataforma_tokenapi` | `TokenAPI` |
| Tabla 28 | `plataforma_registroactividad` | `RegistroActividad` |
| Tabla 29 | `plataforma_preguntafrecuente` | `PreguntaFrecuente` |
| Tabla 30 | `plataforma_configuracionsitio` | `ConfiguracionSitio` |

## 4. Diagramas y su código

| Diagrama | Código principal |
|---|---|
| Flujo de procesos, partes 1 y 2 | `gestion.py` (`crear_solicitud_web`, `cambiar_estado`, `validar_transicion`, `emitir_cotizacion`, `responder_cotizacion`) |
| DA-01 Autenticación | `cuentas.login_view`, `cuentas.verificar_codigo`, `cuentas.reenviar_codigo`, `verificacion.py`, `seguridad.bloqueado` |
| DA-02 Solicitud de creación de sitio web | `cliente.crear_web`, `cliente.estimacion_web`, `static/js/estimador.js`, `gestion.crear_solicitud_web`, `notificaciones.solicitud_registrada` |
| DA-03 Gestión y cotización | `panel.panel_solicitud`, `gestion.emitir_cotizacion`, `gestion.responder_cotizacion`, `static/js/panel.js` |

Estados de una solicitud (códigos en `EstadoSolicitud`): `recibida`, `en_revision`, `cotizada`, `aprobada`, `en_desarrollo`, `completada`, `rechazada` (Cotización rechazada) y `cancelada`.

## 5. Formulario para crear una página web (cuatro pasos)

| Paso | Campos | Dónde se guardan |
|---|---|---|
| 1. Tu proyecto | Nombre del proyecto, tipo de sitio, sitio actual | `Solicitud.titulo`, `RequerimientoWeb.tipo_sitio`, `tiene_sitio_actual`, `url_sitio_actual` |
| 2. Tu negocio | Nombre, rubro, descripción, público y objetivos | `RequerimientoWeb.nombre_negocio`, `rubro`, `descripcion_negocio`, `publico_objetivo`, `objetivos` |
| 3. Funcionalidades | Funcionalidades, integraciones, nivel de diseño y páginas | `funcionalidades`, `integraciones`, `complejidad`, `num_paginas` (calculan la estimación) |
| 4. Diseño y detalles | Estilo, colores, secciones, sitios de referencia, logo, contenido, dominio, presupuesto, fecha y contacto | `estilo_visual`, `colores`, `secciones`, `sitios_referencia`, `situacion_logo`, `tiene_contenido`, `dominio`, `presupuesto`, `Solicitud.fecha_deseada`, `medio_contacto`, `observaciones` |

Los campos de cada paso se definen en `SolicitudWebForm.PASOS` (`forms.py`). El asistente virtual solo aparece en las pantallas para crear una solicitud.

## 6. Cambios frecuentes

| Quiero cambiar... | Dónde |
|---|---|
| Precios de la estimación | `plataforma/estimacion.py` (y se actualiza solo en el navegador) |
| Colores del sitio | `static/css/base.css` (variables `:root`) y `static/css/tema.css` |
| Textos de los correos | `templates/plataforma/correos/` |
| La conexión a PostgreSQL | Archivo `.env`; se comprueba con `python manage.py comprobar_base` |
| El botón de tamaño del texto | `templates/plataforma/includes/cabecera.html`, función `iniciarTamanoTexto` de `static/js/app.js` y las reglas `data-texto` de `static/css/base.css` y `adaptable.css` |
| Servicios, categorías, preguntas frecuentes, datos de contacto y aviso | Panel del equipo (no requiere tocar código) |
| Respuestas del asistente | `plataforma/asistente.py` y las preguntas frecuentes del panel |
| Opciones del paso 4 del formulario | Listas `ESTILOS`, `SECCIONES`, `OPCIONES_LOGO`, `PRESUPUESTOS` y `MEDIOS_CONTACTO` en `RequerimientoWeb` (`models.py`) |

Después de cambiar un modelo hay que ejecutar `python manage.py makemigrations` y `python manage.py migrate`.
Después de cualquier cambio conviene ejecutar `python manage.py test plataforma`.
