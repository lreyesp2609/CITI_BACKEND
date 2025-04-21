from django.urls import include, path
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
    path('tipos_evento/', include([path('crear/', CrearTipoEventoView.as_view(), name='crear_tipo_evento'),
                                   path('listar/', ListarTiposEventoView.as_view(), name='listar_tipos_evento'),
                                   path('editar/<int:id_tipo_evento>/', EditarTipoEventoView.as_view(), name='editar_tipo_evento'),
                                   path('cambiar_estado/<int:id_tipo_evento>/', CambiarEstadoTipoEventoView.as_view(), name='cambiar_estado_tipo_evento'),


])),
]