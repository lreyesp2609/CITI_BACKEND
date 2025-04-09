from django.urls import path
from .views import *

urlpatterns = [
    path('asignar_pastor/', AsignarPastoresView.as_view(), name='asignar_pastor'),
    path('asignar_lider/', AsignarLideresMinisterioView.as_view(), name='asignar_lider'),
]