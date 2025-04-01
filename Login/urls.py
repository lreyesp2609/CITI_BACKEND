from django.urls import path
from .views import *

"""
En esta aplicación, se definen las URLs para las vistas relacionadas con la autenticación.
Las URLs son:
- 'login/': Vista para iniciar sesión.
- 'logout/': Vista para cerrar sesión.
"""

urlpatterns = [
    path('login/', IniciarSesionView.as_view(), name='iniciar_sesion'),
    path('logout/', CerrarSesionView.as_view(), name='cerrar_sesion'),
]