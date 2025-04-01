from django.urls import path
from . import views

urlpatterns = [
    path('crearministerios/', views.CrearMinisterioView.as_view(), name='crear_ministerio'),
]