from django.urls import path
from .views import *

urlpatterns = [
    path('crear/', CrearEventoView.as_view(), name='crear_evento'),  
    path('editar/<int:id_evento>/', EditarEventoView.as_view(), name='editar_evento'),
    path('cancelar/<int:id_evento>/', CancelarEventoView.as_view(), name='cancelar_evento'),
    path('aprobar-rechazar/<int:id_evento>/', AprobarRechazarEventoView.as_view(), name='aprobar_rechazar_evento'),
    path('eventos/', ListarEventosView.as_view(), name='listar_eventos'),
    path('detalle_eventos/<int:id_evento>/', ObtenerEventoView.as_view(), name='obtener_evento'),
    path('mis_eventos/', ListarMisEventosView.as_view(), name='listar_mis_eventos'),
]