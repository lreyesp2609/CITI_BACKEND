from django.urls import path
from .views import *

urlpatterns = [
    path('asignar_pastor/', AsignarPastoresView.as_view(), name='asignar_pastor'),
]