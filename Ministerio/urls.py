from django.urls import path
from . import views
from .views import *

urlpatterns = [
    path('crearministerios/', views.CrearMinisterioView.as_view(), name='crear_ministerio'),
    path('listarministerios/', ListarMinisteriosView.as_view(), name='listar_ministerios'),
    path('editarministerios/<int:id_ministerio>/', EditarMinisterioView.as_view(), name='editar_ministerio'),
]