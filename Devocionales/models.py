from django.db import models
from Login.models import Usuario

class Devocionales(models.Model):
    id_devocional = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, models.DO_NOTHING, db_column='id_usuario')
    mes = models.CharField(max_length=20)  # Ej: "abril"
    año = models.IntegerField()  # Ej: 2025
    fecha = models.DateField()  # Fecha específica del devocional
    titulo = models.TextField()  # Cambiado a TextField para contenido enriquecido
    texto_biblico = models.TextField()
    reflexion = models.TextField()
    contenido_calendario = models.JSONField()  # Para almacenar los datos del calendario
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'devocionales'
