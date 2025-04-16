from django.db import models
from Login.models import Persona, Usuario
from Ciclos.models import Ciclo

# Cursos
class Curso(models.Model):
    id_curso = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    id_ciclo = models.ForeignKey(Ciclo, null=True, on_delete=models.SET_NULL, db_column='id_ciclo')
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    
    class Meta:
        managed = False
        db_table = 'curso'


# Participantes inscritos a un curso
class CursoParticipante(models.Model):
    id_participante = models.AutoField(primary_key=True)
    id_curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    id_persona = models.ForeignKey(Persona, on_delete=models.CASCADE)
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'curso_participante'
        unique_together = ('id_curso', 'id_persona')


# Asistencias a un curso por fecha
class AsistenciaCurso(models.Model):
    id_asistencia = models.AutoField(primary_key=True)
    id_curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    id_persona = models.ForeignKey(Persona, on_delete=models.CASCADE)
    fecha = models.DateField()
    presente = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'asistencia_curso'


# Rúbrica de evaluación por curso
class Rubrica(models.Model):
    id_rubrica = models.AutoField(primary_key=True)
    id_curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    nombre_criterio = models.CharField(max_length=100)
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'rubrica'


# Tareas del curso
class Tarea(models.Model):
    id_tarea = models.AutoField(primary_key=True)
    id_curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    id_criterio = models.ForeignKey(Rubrica, on_delete=models.CASCADE)  # Asociado a la rúbrica
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    fecha_entrega = models.DateField()

    class Meta:
        managed = False
        db_table = 'tarea'


# Calificaciones por tarea
class Calificacion(models.Model):
    id_calificacion = models.AutoField(primary_key=True)
    id_tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE)
    id_persona = models.ForeignKey(Persona, on_delete=models.CASCADE)
    nota = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'calificacion'
