from django.db import models
from Login.models import Usuario

# Create your models here.
class Ministerio(models.Model):
    id_ministerio = models.AutoField(primary_key=True)
    nombre = models.CharField()
    descripcion = models.TextField(blank=True, null=True)
    estado = models.CharField(blank=True, null=True)
    id_lider1 = models.ForeignKey(Usuario, models.DO_NOTHING, db_column='id_lider1', blank=True, null=True)
    id_lider2 = models.ForeignKey(Usuario, models.DO_NOTHING, db_column='id_lider2', related_name='ministerio_id_lider2_set', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ministerio'