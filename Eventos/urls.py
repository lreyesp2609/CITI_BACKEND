from django.urls import path
from .views import *
from . import views

urlpatterns = [
    path('crear/', CrearEventoView.as_view(), name='crear_evento'),  
    path('editar/<int:id_evento>/', EditarEventoView.as_view(), name='editar_evento'),
    path('cancelar-reactivar/<int:id_evento>/', CancelarEventoView.as_view(), name='cancelar_evento'),
    path('aprobar-rechazar/<int:id_evento>/', AprobarRechazarEventoView.as_view(), name='aprobar_rechazar_evento'),
    path('eventos/', ListarEventosView.as_view(), name='listar_eventos'),
    path('detalle_eventos/<int:id_evento>/', ObtenerEventoView.as_view(), name='obtener_evento'),
    path('mis_eventos/', ListarMisEventosView.as_view(), name='listar_mis_eventos'),
    path('evetos_usuarios/', ListarEventosOtrosUsuariosView.as_view(), name='listar_eventos_otros_usuarios'),
    path('notificaciones/', NotificacionesView.as_view(), name='notificaciones'),
    path('notificaciones/respuesta/', ResponderNotificacionView.as_view(), name='responder_notificacion'),
    path('notificaciones/marcar_leida/', views.MarcarNotificacionLeidaView.as_view(), name='marcar_notificacion_leida'),
]