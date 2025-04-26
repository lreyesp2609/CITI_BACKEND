from django.urls import path
from .views import *

urlpatterns = [
    path('crear_devocionales/', DevocionalesView.as_view(), name='devocionales-api'),
    path('devocionales_pdf/<int:id_devocional>/', GenerarPDFDevocional.as_view(), name='generar_pdf'),
    path('historial/', HistorialDevocionalesView.as_view(), name='historial-devocionales'),

]