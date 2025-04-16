from django.db import models

# Ciclos (Ej: Semestre 1-2025)
class Ciclo(models.Model):
    id_ciclo = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        managed = False  
        db_table = 'ciclo'

