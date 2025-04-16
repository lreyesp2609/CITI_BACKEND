from django.urls import path
from .views import *

urlpatterns = [
    path('crear_curso/', CrearCursoView.as_view(), name='crear_curso'),
    path('editar_curso/<int:id_curso>/', EditarCursoView.as_view(), name='editar_curso'),
    path('listar_cursos/<int:id_ciclo>/', ListarCursosView.as_view(), name='listar_cursos'),
    path('ver_curso/<int:id_curso>/', VerCursoView.as_view(), name='ver_curso'),
    path('registrar_participantes/', RegistrarParticipantesCursoView.as_view(), name='registrar_participantes'),
    path('registrar_asistencia_curso/', RegistrarAsistenciaCursoView.as_view(), name='registrar_asistencia_curso'),
    path('crear_tarea/', CrearTareaView.as_view(), name='crear_tarea'),
    path('registrar_calificaciones/', RegistrarCalificacionesView.as_view(), name='registrar_calificaciones'),
    path('editar_tarea/<int:id_tarea>/', EditarTareaView.as_view(), name='editar_tarea'),
    path('listar_tareas_curso/<int:id_curso>/', ListarTareasCursoView.as_view(), name='listar_tareas_curso'), 
    path('ver_calificaciones_alumno/<int:id_persona>/', VerCalificacionesAlumnoView.as_view(), name='ver_calificaciones_alumno'),
]
