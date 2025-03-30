from django.urls import path
from .views import *

urlpatterns = [
    path('decodificar_token/', DecodificarTokenView.as_view(), name='decodificar_token'),
]