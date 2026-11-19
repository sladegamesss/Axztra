// Se carga antes que el resto: marca que JavaScript está activo y aplica el tamaño de texto guardado,
// para que la página no cambie de tamaño al terminar de cargar.
(function () {
    var raiz = document.documentElement;
    raiz.classList.add('con-js');
    try {
        var tamano = window.localStorage.getItem('axztra-texto');
        if (tamano === 'grande' || tamano === 'muy-grande') {
            raiz.setAttribute('data-texto', tamano);
        }
    } catch (error) {
        raiz.removeAttribute('data-texto');
    }
})();
