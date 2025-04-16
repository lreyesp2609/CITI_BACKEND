from django.urls import path
from .views import *

urlpatterns = [
    path('crear_ciclo/', CrearCicloView.as_view(), name='crear_ciclo'),  
    path('editar_ciclo/<int:id_ciclo>/', EditarCicloView.as_view(), name='editar_ciclo'),
    path('listar_ciclos/', ListarCiclosView.as_view(), name='listar_ciclos'),
    path('ver_ciclo/<int:id_ciclo>/', VerCicloView.as_view(), name='ver_ciclo'),
]
