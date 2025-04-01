from django.db import models

class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True)
    rol = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False  
        db_table = 'rol'

class Persona(models.Model):
    id_persona = models.AutoField(primary_key=True)
    numero_cedula = models.CharField(max_length=20, null=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    genero = models.CharField(max_length=20, blank=True, null=True)  
    celular = models.CharField(max_length=20, blank=True, null=True) 
    direccion = models.CharField(max_length=255, blank=True, null=True)  
    correo_electronico = models.CharField(max_length=100, blank=True, null=True)
    nivel_estudio = models.CharField(max_length=50, blank=True, null=True)
    nacionalidad = models.CharField(max_length=30, blank=True, null=True)
    profesion = models.CharField(max_length=50, blank=True, null=True)
    estado_civil = models.CharField(max_length=20, blank=True, null=True)
    lugar_trabajo = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False  
        db_table = 'personas'


class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    id_rol = models.ForeignKey(Rol, on_delete=models.DO_NOTHING, db_column='id_rol')
    id_persona = models.ForeignKey(Persona, on_delete=models.DO_NOTHING, db_column='id_persona')
    usuario = models.CharField(max_length=50)
    contrasenia = models.CharField(max_length=255)

    class Meta:
        managed = False  
        db_table = 'usuarios'
