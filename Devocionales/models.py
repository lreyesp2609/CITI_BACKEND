from django.db import models
from Login.models import Usuario
import json

class Devocionales(models.Model):
    id_devocional = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.DO_NOTHING, db_column='id_usuario')
    mes = models.CharField(max_length=20)
    año = models.IntegerField()
    fecha = models.DateField(auto_now_add=True)  # Coincide con DEFAULT CURRENT_DATE
    titulo = models.TextField()
    texto_biblico = models.TextField()
    reflexion = models.TextField()
    contenido_calendario = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False  # Mantenemos False porque la tabla ya existe
        db_table = 'devocionales'

    def get_contenido_calendario(self):
        return json.loads(self.contenido_calendario)

    def set_contenido_calendario(self, data):
        self.contenido_calendario = json.dumps(data)