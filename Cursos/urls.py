from django.urls import path
from .views import *

urlpatterns = [
    path('crear_curso/', CrearCursoView.as_view(), name='crear_curso'),
    path('editar_criterios_curso/<int:id_curso>/', EditarCriteriosCursoView.as_view(), name='editar_criterios_curso'), 
    path('listar_criterios_curso/<int:id_curso>/', ListarCriteriosCursoView.as_view(), name='listar_criterios_curso'),
    path('editar_curso/<int:id_curso>/', EditarCursoView.as_view(), name='editar_curso'),
    path('listar_cursos/<int:id_ciclo>/', ListarCursosView.as_view(), name='listar_cursos'),
    path('ver_curso/<int:id_curso>/', VerCursoView.as_view(), name='ver_curso'),
    path('registrar_participantes/<int:id_curso>/', RegistrarParticipantesCursoView.as_view(), name='registrar_participantes'),
    path('listar_participantes/<int:id_curso>/', ListarParticipantesCursoView.as_view(), name='listar_participantes_curso'),
    path('registrar_asistencia_curso/', RegistrarAsistenciaCursoView.as_view(), name='registrar_asistencia_curso'),
    path('crear_tarea/', CrearTareaView.as_view(), name='crear_tarea'),
    path('editar_tarea/<int:id_tarea>/', EditarTareaView.as_view(), name='editar_tarea'),
    path('ver_tarea/<int:id_tarea>/', VerTareaView.as_view(), name='ver_tarea'),
    path('registrar_calificaciones/', RegistrarCalificacionesView.as_view(), name='registrar_calificaciones'),
    path('listar_tareas_curso/<int:id_curso>/', ListarTareasCursoView.as_view(), name='listar_tareas_curso'), 
    path('calcular_calificacion/<int:id_curso>/<int:id_persona>/', CalcularCalificacionAlumnoView.as_view(), name='calcular_calificacion'),
    path('listar_calificaciones_tarea/<int:id_tarea>/', ListarCalificacionesTareaView.as_view(), name='listar_calificaciones_tarea'),
    path('ver_calificaciones_alumno/<int:id_persona>/', VerCalificacionesAlumnoView.as_view(), name='ver_calificaciones_alumno'),
]
