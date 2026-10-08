"""
Rutas de la API REST versionada (CU22 Consultar solicitudes vía API, RF12).
"""

from django.urls import path

from . import views

urlpatterns = [
    path('servicios/', views.servicios, name='api_servicios'),
    path('estimaciones/', views.estimaciones, name='api_estimaciones'),
    path('solicitudes/', views.solicitudes, name='api_solicitudes'),
    path('solicitudes/<str:numero>/', views.solicitud, name='api_solicitud'),
]
