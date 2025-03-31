from django.urls import path
from .views import *

urlpatterns = [
    path('personas/', ListarPersonasView.as_view(), name='listar_personas'),
    path('personas/<int:id_persona>/', DetallePersonaView.as_view(), name='detalle_persona'),
    path('editarpersonas/<int:id_persona>/actualizar/', ActualizarPersonaView.as_view(), name='actualizar_persona'),
]