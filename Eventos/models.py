from django.db import models
from Login.models import Persona, Usuario
from Ministerio.models import Ministerio

class EstadoEvento(models.Model):
    id_estado = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'estado_evento'

class Evento(models.Model):
    id_evento = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=255)
    id_ministerio = models.ForeignKey(Ministerio, models.DO_NOTHING, db_column='id_ministerio')
    descripcion = models.TextField(blank=True, null=True)
    fecha = models.DateField()
    hora = models.TimeField()
    lugar = models.CharField(max_length=255, blank=True, null=True)
    id_usuario = models.ForeignKey(Usuario, models.DO_NOTHING, db_column='id_usuario')
    id_estado = models.ForeignKey(EstadoEvento, models.DO_NOTHING, db_column='id_estado', default=1)  # Pendiente por defecto
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'eventos'

class MotivosEvento(models.Model):
    id_motivo = models.AutoField(primary_key=True)
    id_evento = models.ForeignKey(Evento, models.DO_NOTHING, db_column='id_evento')
    id_usuario = models.ForeignKey(Usuario, models.DO_NOTHING, db_column='id_usuario')
    descripcion = models.TextField()
    fecha = models.DateField(auto_now_add=True)
    hora = models.TimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'motivos_evento'

class ParticipantesEvento(models.Model):
    id_participacion = models.AutoField(primary_key=True)
    id_evento = models.ForeignKey(Evento, models.DO_NOTHING, db_column='id_evento')
    id_usuario = models.ForeignKey(Usuario, models.DO_NOTHING, db_column='id_usuario')
    fecha_registro = models.DateTimeField(auto_now_add=True)
    asistencia = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'participantes_evento'
        unique_together = (('id_evento', 'id_usuario'),)