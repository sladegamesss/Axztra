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

    // Formatea un monto con conversión en vivo según la moneda seleccionada.
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

    // ... [resto del código original: interpolar, postJSON, avisar, validaciones, etc. Mismo contenido exacto de tu archivo] ...
    
    // Función para manejar las opciones de idioma y moneda
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
                    if (el.children.length > 1) return; // Evita romper iconos anidados complejos
                    
                    var original = el.getAttribute('data-es') || el.textContent.trim();
                    if (!el.hasAttribute('data-es')) el.setAttribute('data-es', original);
                    
                    if (dict[original]) {
                        if (el.childNodes.length > 0 && el.childNodes[0].nodeType === 3) {
                             el.childNodes[0].nodeValue = dict[original];
                        } else if (el.childNodes.length > 1 && el.childNodes[1].nodeType === 3) {
                             el.childNodes[1].nodeValue = dict[original];
                        } else {
                             el.textContent = dict[original];
                        }
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
    // ... [resto del código: iniciarFoco, iniciarProgreso, iniciarContadores, etc.]

    document.addEventListener('DOMContentLoaded', function () {
        iniciarPalabras();
        iniciarProgreso();
        iniciarTamanoTexto();
        iniciarOpcionesRegionales(); // Nuevo
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
