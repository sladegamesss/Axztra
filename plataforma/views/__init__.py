from django.shortcuts import render


def error_404(request, exception=None):
    return render(request, 'plataforma/error.html', {
        'codigo': 404,
        'titulo': 'No encontramos esta página',
        'mensaje': 'La dirección puede estar mal escrita o la página ya no está disponible.',
    }, status=404)


def error_500(request):
    return render(request, 'plataforma/error.html', {
        'codigo': 500,
        'titulo': 'Ocurrió un error inesperado',
        'mensaje': 'Ya quedó registrado. Intenta nuevamente en unos minutos.',
    }, status=500)
