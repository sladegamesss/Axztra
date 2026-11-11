// AXZTRA: funciones generales del sitio.
//
// Se carga en todas las páginas. Incluye: validación de formularios en el navegador (RNF05),
// avisos, menús desplegables, asistente virtual (CU03), animaciones y efectos de la interfaz.
// Las funciones que empiezan con "iniciar" se ejecutan al cargar la página (ver el final del archivo).

(function () {
    'use strict';

    var AXZTRA = window.AXZTRA = window.AXZTRA || {};

    // Diccionario Básico de Traducción 
    var DICCIONARIO = {
        'en': {
            'Inicio': 'Home',
            'Servicios': 'Services',
            'Mis solicitudes': 'My Requests',
            'Cómo funciona': 'How it works',
            'Nosotros': 'About us',
            'Iniciar sesión': 'Login',
            'Crear cuenta': 'Sign up',
            'Nueva solicitud': 'New request',
            'Menú': 'Menu',
            'Cerrar': 'Close'
        },
        'pt': {
            'Inicio': 'Início',
            'Servicios': 'Serviços',
            'Mis solicitudes': 'Meus pedidos',
            'Cómo funciona': 'Como funciona',
            'Nosotros': 'Sobre nós',
            'Iniciar sesión': 'Entrar',
            'Crear cuenta': 'Cadastrar',
            'Nueva solicitud': 'Novo pedido',
            'Menú': 'Menu',
            'Cerrar': 'Fechar'
        }
    };

    // Configuraciones Regionales
    var configRegional = {
        moneda: localStorage.getItem('axztra-moneda') || 'CLP',
        idioma: localStorage.getItem('axztra-idioma') || 'es',
        tasaCambio: JSON.parse(localStorage.getItem('axztra-tasas') || '{"USD": 0.0010, "ARS": 1.0, "EUR": 0.00095, "BRL": 0.0055, "MXN": 0.020, "CLP": 1}')
    };

    // Actualiza la tasa de cambio en segundo plano sin bloquear el navegador
    function actualizarTasasDeCambio() {
        var ultimaActualizacion = parseInt(localStorage.getItem('axztra-tasas-fecha') || '0', 10);
        var ahora = Date.now();
        // Actualizar cada 12 horas
        if (ahora - ultimaActualizacion < 12 * 60 * 60 * 1000) {
            actualizarTextoTasa();
            return; 
        }

        fetch('https://open.er-api.com/v6/latest/CLP')
            .then(function(res) { return res.json(); })
            .then(function(data) {
                if(data.rates) {
                    configRegional.tasaCambio = {
                        USD: data.rates.USD,
                        ARS: data.rates.ARS,
                        EUR: data.rates.EUR,
                        BRL: data.rates.BRL,
                        MXN: data.rates.MXN,
                        CLP: 1
                    };
                    localStorage.setItem('axztra-tasas', JSON.stringify(configRegional.tasaCambio));
                    localStorage.setItem('axztra-tasas-fecha', ahora.toString());
                    actualizarTextoTasa();
                }
            })
            .catch(function(e) {
                console.warn('No se pudo actualizar la tasa de cambio en vivo.', e);
                actualizarTextoTasa();
            });
    }

    function actualizarTextoTasa() {
        document.querySelectorAll('#tasa-cambio-info, #tasa-cambio-info-pub').forEach(function(el) {
            if (configRegional.moneda === 'CLP') {
                el.textContent = 'Moneda base';
            } else {
                var tasaInversa = (1 / configRegional.tasaCambio[configRegional.moneda]).toFixed(2);
                el.textContent = '1 ' + configRegional.moneda + ' = $' + tasaInversa + ' CLP';
            }
        });
    }

    // Función para manejar las opciones de idioma y moneda (SIN PAÍS)
    function iniciarOpcionesRegionales() {
        actualizarTasasDeCambio();

        var selectoresMoneda = document.querySelectorAll('#selector-moneda, #selector-moneda-pub');
        var selectoresIdioma = document.querySelectorAll('#selector-idioma, #selector-idioma-pub');
        var resumenes = document.querySelectorAll('.region-resumen');
        var indicadoresMovil = document.querySelectorAll('.regional-indicador');

        // Banderas SVG
        var BANDERAS = {
            'CLP': '<svg viewBox="0 0 512 512" width="16" height="16"><rect width="512" height="512" fill="#D52B1E"/><rect width="512" height="256" fill="#fff"/><rect width="170.67" height="256" fill="#0039A6"/><polygon points="85.33,40 102.73,93.55 159.04,93.55 113.48,126.65 130.88,180.2 85.33,147.1 39.79,180.2 57.19,126.65 11.63,93.55 67.94,93.55" fill="#fff"/></svg>',
            'USD': '<svg viewBox="0 0 512 512" width="16" height="16"><rect width="512" height="512" fill="#fff"/><rect width="512" height="39.38" y="472.61" fill="#B22234"/><rect width="512" height="39.38" y="393.84" fill="#B22234"/><rect width="512" height="39.38" y="315.07" fill="#B22234"/><rect width="512" height="39.38" y="236.3" fill="#B22234"/><rect width="512" height="39.38" y="157.53" fill="#B22234"/><rect width="512" height="39.38" y="78.76" fill="#B22234"/><rect width="512" height="39.38" fill="#B22234"/><rect width="204.8" height="275.69" fill="#3C3B6E"/></svg>',
            'ARS': '<svg viewBox="0 0 512 512" width="16" height="16"><rect width="512" height="512" fill="#74ACDF"/><rect width="512" height="170.67" y="170.67" fill="#fff"/><circle cx="256" cy="256" r="40" fill="#F6B40E"/></svg>',
            'EUR': '<svg viewBox="0 0 512 512" width="16" height="16"><rect width="512" height="512" fill="#c60b1e"/><rect width="512" height="256" y="128" fill="#ffc400"/></svg>',
            'BRL': '<svg viewBox="0 0 512 512" width="16" height="16"><rect width="512" height="512" fill="#009b3a"/><polygon points="256,40 480,256 256,472 32,256" fill="#fedf00"/><circle cx="256" cy="256" r="100" fill="#002776"/></svg>',
            'MXN': '<svg viewBox="0 0 512 512" width="16" height="16"><rect width="512" height="512" fill="#fff"/><rect width="170.67" height="512" fill="#006847"/><rect width="170.67" height="512" x="341.33" fill="#ce1126"/><circle cx="256" cy="256" r="40" fill="#8b4513"/></svg>'
        };

        function aplicarTraduccion(idioma) {
            if (idioma === 'es') return;
            var dict = DICCIONARIO[idioma];
            if (!dict) return;

            try {
                document.querySelectorAll('a, button, span, strong, h1, h2, h3, label').forEach(function(el) {
                    if (el.closest('[data-no-traducir]')) return;
                    
                    var original = el.getAttribute('data-es') || (el.textContent ? el.textContent.trim() : '');
                    
                    if (!original || !dict[original]) return;

                    if (!el.hasAttribute('data-es')) {
                        el.setAttribute('data-es', original);
                    }
                    
                    var tieneIconos = el.querySelector('i, svg');
                    if (tieneIconos) {
                        for (var i = 0; i < el.childNodes.length; i++) {
                            if (el.childNodes[i].nodeType === 3 && el.childNodes[i].nodeValue.trim() === original) {
                                el.childNodes[i].nodeValue = " " + dict[original];
                                break;
                            }
                        }
                    } else {
                        el.textContent = dict[original];
                    }
                });
            } catch (e) {
                console.warn('Error menor al traducir la UI', e);
            }
        }

        function refrescarUI() {
            var bandera = BANDERAS[configRegional.moneda] || BANDERAS['CLP'];
            
            resumenes.forEach(function(el) { el.innerHTML = configRegional.moneda.substring(0, 2) + ' ' + bandera; });
            indicadoresMovil.forEach(function(el) { el.textContent = configRegional.moneda + ' / ' + configRegional.idioma.toUpperCase(); });
            
            selectoresMoneda.forEach(function(el) { el.value = configRegional.moneda; });
            selectoresIdioma.forEach(function(el) { el.value = configRegional.idioma; });

            actualizarTextoTasa();
            aplicarTraduccion(configRegional.idioma);
            
            // Dispara el evento input en la portada para que el estimador recalcule los montos visualmente
            var estimadorPortada = document.getElementById('estimador-portada');
            if (estimadorPortada) { 
                try { estimadorPortada.dispatchEvent(new Event('input')); } catch(e){} 
            }
        }

        selectoresMoneda.forEach(function(select) {
            select.addEventListener('change', function(e) {
                configRegional.moneda = e.target.value;
                localStorage.setItem('axztra-moneda', configRegional.moneda);
                refrescarUI();
            });
        });

        selectoresIdioma.forEach(function(select) {
            select.addEventListener('change', function(e) {
                configRegional.idioma = e.target.value;
                localStorage.setItem('axztra-idioma', configRegional.idioma);
                if (configRegional.idioma === 'es') { location.reload(); } else { refrescarUI(); }
            });
        });

        // Asegurar que la UI se refresca sin romper el hilo de ejecución principal
        setTimeout(function() { 
            refrescarUI(); 
        }, 50);
    }

    // Lee una cookie (se usa para el token CSRF).
    function cookie(nombre) {
        var partes = document.cookie ? document.cookie.split(';') : [];
        for (var i = 0; i < partes.length; i++) {
            var par = partes[i].trim();
            if (par.indexOf(nombre + '=') === 0) {
                return decodeURIComponent(par.substring(nombre.length + 1));
            }
        }
        return '';
    }

    // Token CSRF que Django exige en los envíos POST.
    AXZTRA.csrf = function () {
        var campos = document.querySelectorAll('input[name="csrfmiddlewaretoken"]');
        for (var i = 0; i < campos.length; i++) {
            if (campos[i].value) { return campos[i].value; }
        }
        return cookie('csrftoken');
    };

    // Formatea un monto en pesos chilenos y lo convierte a la moneda seleccionada.
    AXZTRA.clp = function (valorCLP) {
        var moneda = configRegional.moneda;
        var tasa = configRegional.tasaCambio[moneda] || 1;
        var valorConvertido = Math.round(valorCLP * tasa);

        switch (moneda) {
            case 'USD': return 'US$ ' + valorConvertido.toLocaleString('en-US');
            case 'ARS': return 'ARS$ ' + valorConvertido.toLocaleString('es-AR');
            case 'EUR': return '€ ' + valorConvertido.toLocaleString('es-ES');
            case 'BRL': return 'R$ ' + valorConvertido.toLocaleString('pt-BR');
            case 'MXN': return 'MXN$ ' + valorConvertido.toLocaleString('es-MX');
            default: return '$' + Math.round(valorCLP).toLocaleString('es-CL');
        }
    };

    var reducirMovimiento = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    AXZTRA.reducirMovimiento = reducirMovimiento;

    // Ejecuta una animación numérica (contadores y montos).
    AXZTRA.interpolar = function (duracion, alAvanzar) {
        if (reducirMovimiento || !window.requestAnimationFrame) {
            alAvanzar(1);
            return function () {};
        }
        var inicio = null;
        var activo = true;
        var paso = function (tiempo) {
            if (!activo) { return; }
            if (inicio === null) { inicio = tiempo; }
            var avance = Math.min(1, (tiempo - inicio) / duracion);
            alAvanzar(1 - Math.pow(1 - avance, 3));
            if (avance < 1) { window.requestAnimationFrame(paso); }
        };
        window.requestAnimationFrame(paso);
        return function () { activo = false; };
    };

    // Envía datos en JSON al servidor (lo usa el asistente).
    AXZTRA.postJSON = function (url, datos) {
        return fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': AXZTRA.csrf(), 'X-Requested-With': 'XMLHttpRequest' },
            body: JSON.stringify(datos || {})
        }).then(function (respuesta) {
            return respuesta.json().catch(function () { return {}; }).then(function (cuerpo) {
                return { ok: respuesta.ok, estado: respuesta.status, datos: cuerpo };
            });
        });
    };

    // Muestra un aviso flotante.
    AXZTRA.avisar = function (texto, tipo) {
        var contenedor = document.querySelector('.avisos-flotantes');
        if (!contenedor) {
            contenedor = document.createElement('div');
            contenedor.className = 'avisos-flotantes';
            contenedor.setAttribute('role', 'status');
            contenedor.setAttribute('aria-live', 'polite');
            document.body.appendChild(contenedor);
        }
        var aviso = document.createElement('div');
        aviso.className = 'aviso-flotante tipo-' + (tipo || 'info');
        var icono = document.createElement('i');
        icono.className = tipo === 'danger' ? 'fa-solid fa-circle-exclamation' : (tipo === 'success' ? 'fa-solid fa-circle-check' : 'fa-solid fa-circle-info');
        var mensaje = document.createElement('span');
        mensaje.textContent = texto;
        var cerrar = document.createElement('button');
        cerrar.type = 'button';
        cerrar.className = 'cerrar';
        cerrar.setAttribute('aria-label', 'Cerrar aviso');
        cerrar.textContent = '×';
        aviso.appendChild(icono);
        aviso.appendChild(mensaje);
        aviso.appendChild(cerrar);
        contenedor.appendChild(aviso);
        prepararAviso(aviso);
    };

    // Cierra los avisos solos después de unos segundos.
    function prepararAviso(aviso) {
        var quitar = function () {
            aviso.classList.add('saliendo');
            setTimeout(function () { aviso.remove(); }, 260);
        };
        var boton = aviso.querySelector('.cerrar');
        if (boton) { boton.addEventListener('click', quitar); }
        if (!aviso.classList.contains('tipo-danger')) {
            var tiempo = document.createElement('span');
            tiempo.className = 'aviso-tiempo';
            tiempo.setAttribute('aria-hidden', 'true');
            aviso.appendChild(tiempo);
            setTimeout(quitar, 6500);
        }
    }

    // Mensaje de error en español según el problema del campo.
    function mensajeValidacion(campo) {
        var v = campo.validity;
        if (v.valueMissing) {
            if (campo.type === 'file') { return 'Selecciona un archivo.'; }
            if (campo.tagName === 'SELECT') { return 'Selecciona una opción.'; }
            return 'Completa este campo.';
        }
        if (v.typeMismatch) { return campo.type === 'email' ? 'Ingresa un correo válido, por ejemplo nombre@empresa.cl.' : 'Revisa el formato de este campo.'; }
        if (v.patternMismatch) { return campo.getAttribute('data-mensaje-formato') || 'Revisa el formato de este campo.'; }
        if (v.tooShort) { return 'Debe tener al menos ' + campo.minLength + ' caracteres.'; }
        if (v.tooLong) { return 'El texto es demasiado largo.'; }
        if (v.rangeUnderflow) { return 'El valor mínimo es ' + campo.min + '.'; }
        if (v.rangeOverflow) { return 'El valor máximo es ' + campo.max + '.'; }
        if (v.stepMismatch || v.badInput) { return 'Ingresa un número válido.'; }
        return campo.validationMessage;
    }

    // Quita el error de un campo.
    function limpiarError(campo) {
        var contenedor = campo.closest('.campo') || campo.parentElement;
        if (contenedor) {
            contenedor.classList.remove('con-error');
            contenedor.querySelectorAll('[data-error-js]').forEach(function (e) { e.remove(); });
        }
        campo.removeAttribute('aria-invalid');
    }

    // Marca un campo con error y muestra el mensaje.
    function marcarError(campo, texto) {
        var contenedor = campo.closest('.campo') || campo.parentElement;
        limpiarError(campo);
        var error = document.createElement('div');
        error.className = 'error';
        error.setAttribute('data-error-js', '1');
        error.textContent = texto;
        if (contenedor) {
            contenedor.classList.add('con-error');
            contenedor.appendChild(error);
        }
        campo.setAttribute('aria-invalid', 'true');
    }

    // Valida todos los campos de un formulario o de un paso (RNF05).
    AXZTRA.validar = function (raiz) {
        var primero = null;
        raiz.querySelectorAll('[data-error-grupo]').forEach(function (e) { e.remove(); });
        raiz.querySelectorAll('input, select, textarea').forEach(function (campo) {
            if (campo.disabled || campo.type === 'hidden' || campo.type === 'checkbox' || campo.type === 'radio') { return; }
            if (campo.closest('[hidden]')) { limpiarError(campo); return; }
            if (!campo.checkValidity()) {
                marcarError(campo, mensajeValidacion(campo));
                primero = primero || campo;
            } else {
                limpiarError(campo);
            }
        });
        raiz.querySelectorAll('[data-requiere-seleccion]').forEach(function (grupo) {
            if (grupo.closest('[hidden]')) { return; }
            if (!grupo.querySelector('input:checked')) {
                var error = document.createElement('div');
                error.className = 'error';
                error.setAttribute('data-error-grupo', '1');
                error.textContent = grupo.getAttribute('data-requiere-seleccion');
                grupo.insertAdjacentElement('afterend', error);
                primero = primero || grupo.querySelector('input');
            }
        });
        raiz.querySelectorAll('[data-requerido-si]').forEach(function (campo) {
            var condicion = raiz.querySelector(campo.getAttribute('data-requerido-si'));
            if (condicion && condicion.checked && !campo.value.trim()) {
                marcarError(campo, campo.getAttribute('data-mensaje-requerido') || 'Completa este campo.');
                primero = primero || campo;
            }
        });
        if (primero) {
            primero.focus({ preventScroll: true });
            primero.scrollIntoView({ behavior: 'smooth', block: 'center' });
            return false;
        }
        return true;
    };

    // Formularios con data-validar: validan antes de enviar y evitan doble envío.
    function iniciarFormularios() {
        document.querySelectorAll('form[data-validar]').forEach(function (form) {
            form.addEventListener('submit', function (e) {
                if (form.dataset.enviando === '1') {
                    e.preventDefault();
                    return;
                }
                if (!form.hasAttribute('data-pasos') && !AXZTRA.validar(form)) {
                    e.preventDefault();
                    return;
                }
                setTimeout(function () {
                    if (e.defaultPrevented) { return; }
                    form.dataset.enviando = '1';
                    form.querySelectorAll('button[type="submit"]').forEach(function (b) { b.setAttribute('aria-disabled', 'true'); });
                    var pulsado = e.submitter && e.submitter.classList.contains('boton') ? e.submitter : form.querySelector('button.boton[type="submit"]');
                    if (pulsado) { pulsado.classList.add('cargando'); }
                }, 0);
            });
            form.addEventListener('input', function (e) {
                if (e.target.matches('input, select, textarea') && e.target.checkValidity()) { limpiarError(e.target); }
            });
            form.addEventListener('change', function (e) {
                if (e.target.type === 'checkbox' || e.target.type === 'radio') {
                    var grupo = e.target.closest('[data-requiere-seleccion]');
                    if (grupo && grupo.nextElementSibling && grupo.nextElementSibling.hasAttribute('data-error-grupo')) {
                        grupo.nextElementSibling.remove();
                    }
                }
            });
        });

        document.querySelectorAll('form[data-confirmar]').forEach(function (form) {
            form.addEventListener('submit', function (e) {
                if (!window.confirm(form.getAttribute('data-confirmar'))) { e.preventDefault(); }
            });
        });

        document.querySelectorAll('button[data-confirmar]').forEach(function (boton) {
            boton.addEventListener('click', function (e) {
                if (!window.confirm(boton.getAttribute('data-confirmar'))) { e.preventDefault(); }
            });
        });
    }

    // Menús desplegables (usuario, menú del celular).
    function iniciarDesplegables() {
        document.addEventListener('click', function (e) {
            document.querySelectorAll('details[data-desplegable][open]').forEach(function (d) {
                if (!d.contains(e.target)) { d.removeAttribute('open'); }
            });
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                document.querySelectorAll('details[data-desplegable][open]').forEach(function (d) {
                    d.removeAttribute('open');
                    var s = d.querySelector('summary');
                    if (s) { s.focus(); }
                });
            }
        });
    }

    // Campos que aparecen según otra respuesta (ej: dirección del sitio actual).
    function iniciarAlternables() {
        document.querySelectorAll('[data-muestra-si]').forEach(function (bloque) {
            var regla = bloque.getAttribute('data-muestra-si');
            var corte = regla.lastIndexOf('=');
            var controles = document.querySelectorAll(regla.slice(0, corte));
            var valor = regla.slice(corte + 1);
            var actualizar = function () {
                var marcado = Array.prototype.some.call(controles, function (c) { return c.checked && c.value === valor; });
                bloque.hidden = !marcado;
            };
            controles.forEach(function (c) { c.addEventListener('change', actualizar); });
            actualizar();
        });
    }

    // Formulario de contacto de la portada: arma el mensaje y lo abre en WhatsApp.
    function iniciarContactoWhatsapp() {
        var form = document.getElementById('form-contacto');
        if (!form) { return; }
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            if (!AXZTRA.validar(form)) { return; }
            var nombre = form.querySelector('[name="nombre"]').value.trim();
            var servicio = form.querySelector('[name="servicio"]');
            var mensaje = form.querySelector('[name="mensaje"]').value.trim();
            var texto = 'Hola, soy ' + nombre + '. Me interesa: ' + servicio.options[servicio.selectedIndex].text + '.';
            if (mensaje) { texto += ' ' + mensaje; }
            window.open('https://wa.me/' + form.getAttribute('data-whatsapp') + '?text=' + encodeURIComponent(texto), '_blank', 'noopener');
        });
    }

    // Asistente virtual (CU03). Solo existe en las pantallas de solicitud, por eso revisa si la ventana está.
    function iniciarAsistente() {
        var boton = document.getElementById('asistente-boton');
        var ventana = document.getElementById('asistente-ventana');
        if (!boton || !ventana) { return; }

        var lista = ventana.querySelector('.asistente-mensajes');
        var sugerencias = ventana.querySelector('.asistente-sugerencias');
        var form = ventana.querySelector('.asistente-formulario');
        var entrada = form.querySelector('#asistente-entrada');
        var enviar = form.querySelector('button[type="submit"]');
        var invitacion = document.getElementById('asistente-invitacion');
        var cargado = false;
        var ocupado = false;

        var agregar = function (texto, esBot, acciones) {
            var burbuja = document.createElement('div');
            burbuja.className = 'burbuja ' + (esBot ? 'burbuja-bot' : 'burbuja-usuario');
            burbuja.textContent = texto;
            if (acciones && acciones.length) {
                var caja = document.createElement('div');
                caja.className = 'burbuja-acciones';
                acciones.forEach(function (accion) {
                    var enlace = document.createElement('a');
                    enlace.href = accion.url;
                    enlace.textContent = accion.texto;
                    caja.appendChild(enlace);
                });
                burbuja.appendChild(caja);
            }
            lista.appendChild(burbuja);
            if (esBot && burbuja.offsetHeight > lista.clientHeight * 0.6) {
                lista.scrollTop = burbuja.offsetTop - lista.offsetTop - 12;
            } else {
                lista.scrollTop = lista.scrollHeight;
            }
        };

        var mostrarSugerencias = function (items) {
            sugerencias.textContent = '';
            (items || []).forEach(function (texto) {
                var b = document.createElement('button');
                b.type = 'button';
                b.textContent = texto;
                b.addEventListener('click', function () { mandar(texto); });
                sugerencias.appendChild(b);
            });
        };

        var escribiendo = function (activo) {
            var actual = lista.querySelector('.escribiendo');
            if (activo && !actual) {
                var el = document.createElement('div');
                el.className = 'escribiendo';
                el.setAttribute('aria-label', 'El asistente está escribiendo');
                for (var i = 0; i < 3; i++) { el.appendChild(document.createElement('span')); }
                lista.appendChild(el);
                lista.scrollTop = lista.scrollHeight;
            } else if (!activo && actual) {
                actual.remove();
            }
        };

        var mandar = function (texto) {
            texto = (texto || '').trim();
            if (!texto || ocupado) { return; }
            ocupado = true;
            enviar.disabled = true;
            agregar(texto, false);
            mostrarSugerencias([]);
            entrada.value = '';
            escribiendo(true);
            AXZTRA.postJSON(ventana.getAttribute('data-url-mensaje'), { mensaje: texto })
                .then(function (r) {
                    escribiendo(false);
                    if (!r.ok) {
                        agregar(r.datos.error || 'No pude procesar tu mensaje. Intenta nuevamente.', true);
                        return;
                    }
                    agregar(r.datos.respuesta, true, r.datos.acciones);
                    mostrarSugerencias(r.datos.sugerencias);
                })
                .catch(function () {
                    escribiendo(false);
                    agregar('No hay conexión con el servidor. Revisa tu internet e intenta de nuevo.', true);
                })
                .then(function () {
                    ocupado = false;
                    enviar.disabled = false;
                    entrada.focus();
                });
        };

        var cargarHistorial = function () {
            if (cargado) { return; }
            cargado = true;
            var saludo = ventana.getAttribute('data-saludo');
            fetch(ventana.getAttribute('data-url-historial'), { credentials: 'same-origin' })
                .then(function (r) { return r.json(); })
                .then(function (datos) {
                    if (datos.mensajes && datos.mensajes.length) {
                        datos.mensajes.forEach(function (m) { agregar(m.texto, m.es_asistente); });
                        if (saludo) { agregar(saludo, true); }
                    } else {
                        agregar(saludo || datos.saludo, true);
                    }
                    mostrarSugerencias(datos.sugerencias);
                })
                .catch(function () {
                    agregar(saludo || 'Hola, soy el asistente de AXZTRA. ¿En qué te puedo ayudar?', true);
                });
        };

        var abrir = function () {
            ventana.hidden = false;
            boton.setAttribute('aria-expanded', 'true');
            if (invitacion) { invitacion.remove(); invitacion = null; }
            cargarHistorial();
            setTimeout(function () { entrada.focus(); }, 30);
        };

        var cerrar = function () {
            ventana.hidden = true;
            boton.setAttribute('aria-expanded', 'false');
            boton.focus();
        };

        AXZTRA.abrirAsistente = abrir;

        boton.addEventListener('click', function () {
            if (ventana.hidden) { abrir(); } else { cerrar(); }
        });
        ventana.querySelector('[data-cerrar-asistente]').addEventListener('click', cerrar);
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && !ventana.hidden) { cerrar(); }
        });
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            mandar(entrada.value);
        });
        document.querySelectorAll('[data-abrir-asistente]').forEach(function (el) {
            el.addEventListener('click', function (e) {
                e.preventDefault();
                abrir();
            });
        });
        if (invitacion) {
            invitacion.querySelector('.cerrar').addEventListener('click', function (e) {
                e.stopPropagation();
                invitacion.remove();
                invitacion = null;
            });
            invitacion.addEventListener('click', abrir);
            invitacion.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); abrir(); }
            });
        }
    }

    // Baja la conversación hasta el último mensaje.
    function iniciarConversacion() {
        document.querySelectorAll('.conversacion').forEach(function (c) { c.scrollTop = c.scrollHeight; });
    }

    // Botón para imprimir o guardar la cotización como PDF.
    function iniciarImpresion() {
        document.querySelectorAll('[data-imprimir]').forEach(function (b) {
            b.addEventListener('click', function () { window.print(); });
        });
    }

    window.addEventListener('pageshow', function (e) {
        if (!e.persisted) { return; }
        document.querySelectorAll('form[data-enviando]').forEach(function (form) {
            delete form.dataset.enviando;
            form.querySelectorAll('button[aria-disabled]').forEach(function (b) { b.removeAttribute('aria-disabled'); });
            form.querySelectorAll('.cargando').forEach(function (b) { b.classList.remove('cargando'); });
        });
    });

    var SELECTORES_REVELADO = [
        '.seccion-encabezado', '.opcion-servicio', '.ficha-servicio', '.plan', '.pasos-proceso > li', '.ventaja',
        '.preguntas > details', '.bloque-contacto', '.persona', '.tarjeta', '.fila-solicitud', '.linea-tiempo > li',
        '.texto-legal > h2', '.texto-legal > p', '.lista-solicitudes', '.pestanas', '.equipo', '.planes'
    ].join(', ');

    // Hace aparecer las secciones al bajar por la página.
    function iniciarRevelado() {
        var candidatos = Array.prototype.filter.call(document.querySelectorAll(SELECTORES_REVELADO), function (el) {
            return !el.closest('.panel, .documento') && !(el.parentElement && el.parentElement.closest(SELECTORES_REVELADO));
        });
        var marcarRevelado = function (el) { el.classList.add('revelado'); };
        if (!candidatos.length) { return; }
        if (reducirMovimiento || !('IntersectionObserver' in window)) {
            candidatos.forEach(marcarRevelado);
            return;
        }
        var alto = window.innerHeight || document.documentElement.clientHeight;
        var porPadre = new Map();
        var ocultos = [];
        candidatos.forEach(function (el) {
            if (el.getBoundingClientRect().top < alto * 0.92) {
                marcarRevelado(el);
                return;
            }
            var indice = porPadre.get(el.parentElement) || 0;
            porPadre.set(el.parentElement, indice + 1);
            el.style.setProperty('--retardo', ((indice % 4) * 120) + 'ms');
            el.classList.add('revelar');
            ocultos.push(el);
        });
        var terminar = function (el) {
            el.classList.remove('revelar', 'visible');
            el.style.removeProperty('--retardo');
            marcarRevelado(el);
        };
        var observador = new IntersectionObserver(function (entradas) {
            entradas.forEach(function (entrada) {
                if (!entrada.isIntersecting) { return; }
                var el = entrada.target;
                observador.unobserve(el);
                el.classList.add('visible');
                var listo = false;
                var cerrar = function () {
                    if (listo) { return; }
                    listo = true;
                    terminar(el);
                };
                el.addEventListener('transitionend', function (ev) { if (ev.target === el && ev.propertyName === 'opacity') { cerrar(); } });
                setTimeout(cerrar, 1200);
            });
        }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
        ocultos.forEach(function (el) { observador.observe(el); });
    }

    // Contadores que suben hasta su valor (panel y planes).
    function iniciarContadores() {
        var elementos = document.querySelectorAll('[data-contar]');
        if (!elementos.length || reducirMovimiento) { return; }
        var escribir = function (el, valor) {
            el.textContent = el.getAttribute('data-formato') === 'clp' ? AXZTRA.clp(valor) : Math.round(valor).toLocaleString('es-CL');
        };
        var contar = function (el) {
            var destino = parseFloat(el.getAttribute('data-contar'));
            if (!isFinite(destino) || destino <= 0) { return; }
            AXZTRA.interpolar(1100, function (avance) { escribir(el, destino * avance); });
        };
        var pendientes = Array.prototype.filter.call(elementos, function (el) {
            var destino = parseFloat(el.getAttribute('data-contar'));
            if (isFinite(destino) && destino > 0) { escribir(el, 0); return true; }
            return false;
        });
        if (!('IntersectionObserver' in window)) {
            pendientes.forEach(contar);
            return;
        }
        var observador = new IntersectionObserver(function (entradas) {
            entradas.forEach(function (entrada) {
                if (entrada.isIntersecting) {
                    observador.unobserve(entrada.target);
                    contar(entrada.target);
                }
            });
        }, { threshold: 0.4 });
        pendientes.forEach(function (el) { observador.observe(el); });
    }

    // Sombra de la cabecera al bajar por la página.
    function iniciarCabecera() {
        var cabecera = document.getElementById('cabecera');
        if (!cabecera) { return; }
        var pendiente = false;
        var revisar = function () {
            pendiente = false;
            cabecera.classList.toggle('con-sombra', window.scrollY > 8);
        };
        window.addEventListener('scroll', function () {
            if (!pendiente) {
                pendiente = true;
                window.requestAnimationFrame(revisar);
            }
        }, { passive: true });
        revisar();
    }

    // Tamaños de texto disponibles y el nombre que se muestra en el aviso.
    var TAMANOS_TEXTO = ['normal', 'grande', 'muy-grande'];
    var NOMBRES_TEXTO = { 'normal': 'normal', 'grande': 'grande', 'muy-grande': 'muy grande' };

    // Tamaño de texto que está aplicado en la página.
    function tamanoTextoActual() {
        return document.documentElement.getAttribute('data-texto') || 'normal';
    }

    // Aplica un tamaño, lo guarda en el navegador (clave axztra-texto) y actualiza los botones.
    function aplicarTamanoTexto(tamano, anunciar) {
        var raiz = document.documentElement;
        if (tamano === 'normal') {
            raiz.removeAttribute('data-texto');
        } else {
            raiz.setAttribute('data-texto', tamano);
        }
        try {
            window.localStorage.setItem('axztra-texto', tamano);
        } catch (error) {
            raiz.setAttribute('data-texto-temporal', tamano);
        }
        document.querySelectorAll('[data-texto-opcion]').forEach(function (b) {
            b.setAttribute('aria-pressed', b.getAttribute('data-texto-opcion') === tamano ? 'true' : 'false');
        });
        document.querySelectorAll('[data-tamano-texto]').forEach(function (b) {
            b.setAttribute('aria-label', 'Tamaño del texto: ' + NOMBRES_TEXTO[tamano] + '. Pulsa para cambiarlo');
            b.setAttribute('title', 'Tamaño del texto: ' + NOMBRES_TEXTO[tamano]);
        });
        if (anunciar) { AXZTRA.avisar('Tamaño del texto: ' + NOMBRES_TEXTO[tamano] + '.', 'success'); }
    }

    // Botón de la cabecera (cambia al siguiente tamaño) y selector A, A+ y A++ del menú del celular.
    function iniciarTamanoTexto() {
        aplicarTamanoTexto(tamanoTextoActual(), false);
        document.querySelectorAll('[data-tamano-texto]').forEach(function (boton) {
            boton.addEventListener('click', function () {
                var siguiente = TAMANOS_TEXTO[(TAMANOS_TEXTO.indexOf(tamanoTextoActual()) + 1) % TAMANOS_TEXTO.length];
                aplicarTamanoTexto(siguiente, true);
            });
        });
        document.querySelectorAll('[data-texto-opcion]').forEach(function (boton) {
            boton.addEventListener('click', function () {
                aplicarTamanoTexto(boton.getAttribute('data-texto-opcion'), false);
            });
        });
    }

    // Botón de ojo para mostrar u ocultar la contraseña.
    // Botón de ojo para mostrar u ocultar la contraseña.
    function iniciarClaves() {
        // Ocultar el ojo nativo de navegadores como Edge para que no se duplique
        if (!document.getElementById('ocultar-ojo-nativo')) {
            var estilo = document.createElement('style');
            estilo.id = 'ocultar-ojo-nativo';
            estilo.textContent = 'input::-ms-reveal, input::-ms-clear { display: none !important; }';
            document.head.appendChild(estilo);
        }

        document.querySelectorAll('input[type="password"].control').forEach(function (campo) {
            if (campo.parentElement.classList.contains('control-clave')) { return; }
            var envoltura = document.createElement('span');
            envoltura.className = 'control-clave';
            campo.parentNode.insertBefore(envoltura, campo);
            envoltura.appendChild(campo);
            var boton = document.createElement('button');
            boton.type = 'button';
            boton.className = 'ver-clave';
            boton.setAttribute('aria-label', 'Mostrar contraseña');
            boton.setAttribute('aria-pressed', 'false');
            var icono = document.createElement('i');
            icono.className = 'fa-regular fa-eye';
            icono.setAttribute('aria-hidden', 'true');
            boton.appendChild(icono);
            envoltura.appendChild(boton);
            boton.addEventListener('click', function () {
                var mostrar = campo.type === 'password';
                campo.type = mostrar ? 'text' : 'password';
                icono.className = mostrar ? 'fa-regular fa-eye-slash' : 'fa-regular fa-eye';
                boton.setAttribute('aria-label', mostrar ? 'Ocultar contraseña' : 'Mostrar contraseña');
                boton.setAttribute('aria-pressed', mostrar ? 'true' : 'false');
                campo.focus();
            });
            if (campo.form) {
                campo.form.addEventListener('submit', function () { campo.type = 'password'; });
            }
        });
    }
    // Título de la portada que aparece palabra por palabra.
    function iniciarPalabras() {
        document.querySelectorAll('[data-palabras]').forEach(function (titulo) {
            if (reducirMovimiento) {
                titulo.classList.add('palabras-listas');
                return;
            }
            var indice = 0;
            Array.prototype.slice.call(titulo.childNodes).forEach(function (nodo) {
                if (nodo.nodeType === 1) {
                    nodo.classList.add('palabra');
                    nodo.style.setProperty('--i', indice++);
                    return;
                }
                if (nodo.nodeType !== 3) { return; }
                var fragmento = document.createDocumentFragment();
                nodo.textContent.split(/(\s+)/).forEach(function (parte) {
                    if (!parte) { return; }
                    if (/^\s+$/.test(parte)) {
                        fragmento.appendChild(document.createTextNode(parte));
                        return;
                    }
                    var palabra = document.createElement('span');
                    palabra.className = 'palabra';
                    palabra.style.setProperty('--i', indice++);
                    palabra.textContent = parte;
                    fragmento.appendChild(palabra);
                });
                titulo.replaceChild(fragmento, nodo);
            });
            titulo.classList.add('palabras-listas');
        });
    }

    // Brillo que sigue al mouse sobre las tarjetas.
    function iniciarFoco() {
        if (reducirMovimiento || !window.matchMedia || !window.matchMedia('(pointer: fine)').matches) { return; }
        var selector = '.ficha-servicio, .opcion-servicio, .plan, .persona, .metrica, .tarjeta';
        document.querySelectorAll(selector).forEach(function (el) {
            if (!el.closest('.documento')) { el.classList.add('foco'); }
        });
        document.addEventListener('pointermove', function (e) {
            var objetivo = e.target && e.target.closest ? e.target.closest('.foco') : null;
            if (!objetivo) { return; }
            var caja = objetivo.getBoundingClientRect();
            objetivo.style.setProperty('--x', (e.clientX - caja.left) + 'px');
            objetivo.style.setProperty('--y', (e.clientY - caja.top) + 'px');
        }, { passive: true });
    }

    // Barra superior que muestra cuánto se ha leído de la página.
    function iniciarProgreso() {
        var barra = document.getElementById('progreso-lectura');
        if (!barra) { return; }
        var pendiente = false;
        var actualizar = function () {
            pendiente = false;
            var total = document.documentElement.scrollHeight - window.innerHeight;
            var avance = total > 0 ? Math.min(1, Math.max(0, window.scrollY / total)) : 0;
            barra.style.transform = 'scaleX(' + avance.toFixed(4) + ')';
        };
        window.addEventListener('scroll', function () {
            if (!pendiente) {
                pendiente = true;
                window.requestAnimationFrame(actualizar);
            }
        }, { passive: true });
        window.addEventListener('resize', actualizar);
        actualizar();
    }

    // Preguntas frecuentes que se abren con suavidad.
    function iniciarAcordeon() {
        if (reducirMovimiento || !Element.prototype.animate) { return; }
        document.querySelectorAll('.preguntas details').forEach(function (detalle) {
            var resumen = detalle.querySelector('summary');
            var animacion = null;
            resumen.addEventListener('click', function (e) {
                e.preventDefault();
                if (animacion) { animacion.cancel(); }
                detalle.style.overflow = 'hidden';
                var abrir = !detalle.open;
                var inicio = detalle.offsetHeight;
                if (abrir) { detalle.open = true; }
                var fin = abrir ? detalle.offsetHeight : resumen.offsetHeight;
                animacion = detalle.animate({ height: [inicio + 'px', fin + 'px'] }, { duration: 320, easing: 'cubic-bezier(0.2, 0.7, 0.2, 1)' });
                animacion.onfinish = function () {
                    animacion = null;
                    if (!abrir) { detalle.open = false; }
                    detalle.style.overflow = '';
                };
                animacion.oncancel = function () { detalle.style.overflow = ''; };
            });
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        iniciarPalabras();
        iniciarProgreso();
        iniciarTamanoTexto();
        iniciarOpcionesRegionales();
        iniciarClaves();
        document.querySelectorAll('.aviso-flotante').forEach(prepararAviso);
        iniciarFormularios();
        iniciarDesplegables();
        iniciarAlternables();
        iniciarContactoWhatsapp();
        iniciarAsistente();
        iniciarConversacion();
        iniciarImpresion();
        iniciarCabecera();
        iniciarRevelado();
        iniciarContadores();
        iniciarFoco();
        iniciarAcordeon();
    });
})();
