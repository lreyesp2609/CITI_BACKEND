from django.db import models
from decimal import Decimal
from Login.models import Persona, Usuario
from Ciclos.models import Ciclo
from django.core.exceptions import ValidationError

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
    id_curso = models.ForeignKey(Curso, on_delete=models.CASCADE, db_column='id_curso')
    id_persona = models.ForeignKey(Persona, on_delete=models.CASCADE, db_column='id_persona')
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'curso_participante'
        unique_together = ('id_curso', 'id_persona')


# Asistencias a un curso por fecha
class AsistenciaCurso(models.Model):
    id_asistencia = models.AutoField(primary_key=True)
    id_curso = models.ForeignKey(Curso, on_delete=models.CASCADE, db_column='id_curso')
    id_persona = models.ForeignKey(Persona, on_delete=models.CASCADE, db_column='id_persona')
    fecha = models.DateField()
    presente = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'asistencia_curso'


# Rúbrica de evaluación por curso
class Rubrica(models.Model):
    id_rubrica = models.AutoField(primary_key=True)
    id_curso = models.ForeignKey(Curso, on_delete=models.CASCADE, db_column='id_curso')
    nombre_criterio = models.CharField(max_length=100)
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2)
    
    def clean(self):
        # Validar que el porcentaje esté entre 0 y 100
        if self.porcentaje < Decimal('0') or self.porcentaje > Decimal('100'):
            raise ValidationError("El porcentaje debe estar entre 0 y 100")
        
        # Validar que la suma de porcentajes no exceda 100%
        if not self.pk:  # Solo para nuevos registros
            rubricas_existentes = Rubrica.objects.filter(id_curso=self.id_curso)
            total = sum(r.porcentaje for r in rubricas_existentes) + self.porcentaje
            if total > Decimal('100'):
                raise ValidationError(f"La suma de porcentajes excede 100% (actual: {total}%)")
    
    def save(self, *args, **kwargs):
        self.full_clean()  # Ejecuta las validaciones
        super().save(*args, **kwargs)

    class Meta:
        managed = False
        db_table = 'rubrica'


# Tareas del curso
class Tarea(models.Model):
    id_tarea = models.AutoField(primary_key=True)
    id_curso = models.ForeignKey(Curso, on_delete=models.CASCADE, db_column='id_curso')
    id_criterio = models.ForeignKey(Rubrica, on_delete=models.CASCADE, db_column='id_criterio')
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    fecha_entrega = models.DateField()

    class Meta:
        managed = False
        db_table = 'tarea'


# Calificaciones por tarea
class Calificacion(models.Model):
    id_calificacion = models.AutoField(primary_key=True)
    id_tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE, db_column='id_tarea')
    id_persona = models.ForeignKey(Persona, on_delete=models.CASCADE, db_column='id_persona')
    nota = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'calificacion'
