from django.urls import path
from .views import *

"""
En esta aplicación, se definen las URLs para las vistas relacionadas con el registro de usuarios.
Las URLs son:
- 'register/': Vista para registrar un nuevo usuario.
- 'cambiar-contrasenia/<int:id_usuario>/': Vista para cambiar la contraseña de un usuario.
"""

urlpatterns = [
    path('register/', RegistrarUsuarioView.as_view(), name='registrar_usuario'),
    path('cambiar-contrasenia/<int:id_usuario>/', CambiarContraseniaView.as_view(), name='cambiar_contrasenia'),
]