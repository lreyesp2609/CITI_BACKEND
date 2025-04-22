from django.http import JsonResponse
from django.views import View
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import jwt
import json
from .models import *
from django.conf import settings

@method_decorator(csrf_exempt, name='dispatch')
class CrearCursoView(View):
    def post(self, request, *args, **kwargs):
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)

            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                id_usuario = payload.get('id_usuario')
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            required_fields = ['nombre', 'descripcion', 'id_ciclo', 'fecha_inicio', 'fecha_fin', 'hora_inicio', 'hora_fin']
            for field in required_fields:
                if field not in request.POST:
                    return JsonResponse({'error': f'El campo {field} es obligatorio'}, status=400)

            with transaction.atomic():
                curso = Curso.objects.create(
                    nombre=request.POST['nombre'],
                    descripcion=request.POST['descripcion'],
                    id_ciclo_id=request.POST['id_ciclo'],
                    fecha_inicio=request.POST['fecha_inicio'],
                    fecha_fin=request.POST['fecha_fin'],
                    hora_inicio=request.POST['hora_inicio'],
                    hora_fin=request.POST['hora_fin'],
                    id_usuario_id=id_usuario
                )

                # Crear rúbrica por defecto
                criterios_por_defecto = [
                    ('Asistencia', 10.00),
                    ('Actuación', 30.00),
                    ('Tareas', 30.00),
                    ('Examen', 30.00),
                ]

                for nombre, porcentaje in criterios_por_defecto:
                    Rubrica.objects.create(
                        id_curso=curso,
                        nombre_criterio=nombre,
                        porcentaje=porcentaje
                    )

                return JsonResponse({
                    'mensaje': 'Curso creado exitosamente',
                    'id_curso': curso.id_curso
                }, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class EditarCursoView(View):
    def post(self, request, id_curso, *args, **kwargs):
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)

            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                id_usuario = payload.get('id_usuario')
                rol = payload.get('rol')
                rol_id = 1 if rol == "Pastor" else 2

            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            # Buscar el curso
            try:
                curso = Curso.objects.get(id_curso=id_curso)
            except Curso.DoesNotExist:
                return JsonResponse({'error': 'El curso no existe'}, status=404)

            # Actualizar campos si están en el request
            for field in ['nombre', 'descripcion', 'fecha_inicio', 'fecha_fin', 'hora_inicio', 'hora_fin']:
                if field in request.POST:
                    setattr(curso, field, request.POST[field])

            # Cambiar ciclo si se manda otro id
            if 'id_ciclo' in request.POST:
                try:
                    ciclo = Ciclo.objects.get(id_ciclo=request.POST['id_ciclo'])
                    curso.id_ciclo = ciclo
                except Ciclo.DoesNotExist:
                    return JsonResponse({'error': 'El nuevo ciclo no existe'}, status=404)

            curso.save()

            return JsonResponse({
                'mensaje': 'Curso actualizado correctamente',
                'id_curso': curso.id_curso
            }, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ListarCursosView(View):
    def get(self, request, *args, **kwargs):
        try:
            # Obtener el id_ciclo desde los parámetros de la URL
            id_ciclo = kwargs.get('id_ciclo')
            
            # Filtrar los cursos por ciclo
            cursos = Curso.objects.filter(id_ciclo=id_ciclo).select_related('id_ciclo', 'id_usuario')
            
            # Crear la respuesta con los cursos filtrados
            data = []
            for curso in cursos:
                data.append({
                    'id_curso': curso.id_curso,
                    'nombre': curso.nombre,
                    'descripcion': curso.descripcion,
                    'id_ciclo': curso.id_ciclo.id_ciclo,
                    'nombre_ciclo': curso.id_ciclo.nombre,
                    'fecha_inicio': curso.fecha_inicio,
                    'fecha_fin': curso.fecha_fin,
                    'hora_inicio': curso.hora_inicio,
                    'hora_fin': curso.hora_fin,
                    'id_usuario': curso.id_usuario.id_usuario,
                })

            return JsonResponse(data, safe=False, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class VerCursoView(View):
    def get(self, request, id_curso, *args, **kwargs):
        try:
            curso = Curso.objects.select_related('id_ciclo', 'id_usuario').get(id_curso=id_curso)
            data = {
                'id_curso': curso.id_curso,
                'nombre': curso.nombre,
                'descripcion': curso.descripcion,
                'id_ciclo': curso.id_ciclo.id_ciclo,
                'nombre_ciclo': curso.id_ciclo.nombre,
                'fecha_inicio': curso.fecha_inicio,
                'fecha_fin': curso.fecha_fin,
                'hora_inicio': curso.hora_inicio,
                'hora_fin': curso.hora_fin,
                'id_usuario': curso.id_usuario.id_usuario,
            }
            return JsonResponse(data, status=200)
        except Curso.DoesNotExist:
            return JsonResponse({'error': 'Curso no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class RegistrarParticipantesCursoView(View):
    def post(self, request, *args, **kwargs):
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)

            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                id_usuario = payload.get('id_usuario')
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            data = json.loads(request.body.decode('utf-8'))

            id_curso = data.get('id_curso')
            participantes_ids = data.get('participantes')  # lista de id_persona

            if not id_curso or not isinstance(participantes_ids, list):
                return JsonResponse({'error': 'Faltan datos o participantes no es una lista'}, status=400)

            try:
                curso = Curso.objects.get(pk=id_curso)
            except Curso.DoesNotExist:
                return JsonResponse({'error': 'Curso no encontrado'}, status=404)

            with transaction.atomic():
                # Participantes actuales
                actuales = set(
                    CursoParticipante.objects.filter(id_curso=curso)
                    .values_list('id_persona', flat=True)
                )

                nuevos = set(participantes_ids)

                # Participantes a eliminar
                eliminar = actuales - nuevos
                # Participantes a agregar
                agregar = nuevos - actuales

                # Eliminar los que ya no están
                CursoParticipante.objects.filter(id_curso=curso, id_persona__in=eliminar).delete()

                # Agregar nuevos
                for id_persona in agregar:
                    try:
                        persona = Persona.objects.get(pk=id_persona)
                        CursoParticipante.objects.create(
                            id_curso=curso,
                            id_persona=persona
                        )
                    except Persona.DoesNotExist:
                        return JsonResponse({'error': f'Persona con ID {id_persona} no existe'}, status=404)

            return JsonResponse({
                'mensaje': 'Participantes actualizados correctamente',
                'agregados': list(agregar),
                'eliminados': list(eliminar)
            }, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ListarParticipantesCursoView(View):
    def get(self, request, *args, **kwargs):
        try:
            id_curso = kwargs.get('id_curso')
            participantes = CursoParticipante.objects.filter(id_curso=id_curso).select_related('id_persona')
            
            if not participantes.exists():
                return JsonResponse([], safe=False, status=200)

            data = []
            for participante in participantes:
                data.append({
                    'id_persona': participante.id_persona.id_persona,
                    'nombre': participante.id_persona.nombres,
                    'apellido': participante.id_persona.apellidos,
                })

            return JsonResponse(data, safe=False, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class RegistrarAsistenciaCursoView(View):
    def post(self, request, *args, **kwargs):
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)

            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                id_usuario = payload.get('id_usuario')
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            data = json.loads(request.body.decode('utf-8'))

            id_curso = data.get('id_curso')
            fecha = data.get('fecha')
            asistencias = data.get('asistencias')

            if not id_curso or not fecha or not isinstance(asistencias, list):
                return JsonResponse({'error': 'Datos incompletos'}, status=400)

            try:
                curso = Curso.objects.get(pk=id_curso)
            except Curso.DoesNotExist:
                return JsonResponse({'error': 'Curso no encontrado'}, status=404)

            with transaction.atomic():
                for item in asistencias:
                    id_persona = item.get('id_persona')
                    presente = item.get('presente', False)

                    if not id_persona:
                        continue

                    asistencia, created = AsistenciaCurso.objects.update_or_create(
                        id_curso=curso,
                        id_persona_id=id_persona,
                        fecha=fecha,
                        defaults={'presente': presente}
                    )

            return JsonResponse({'mensaje': 'Asistencias registradas correctamente'}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class CrearTareaView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            required_fields = ['id_curso', 'id_criterio', 'titulo', 'fecha_entrega']
            for field in required_fields:
                if field not in data:
                    return JsonResponse({'error': f'El campo {field} es obligatorio'}, status=400)

            tarea = Tarea.objects.create(
                id_curso_id=data['id_curso'],
                id_criterio_id=data['id_criterio'], 
                titulo=data['titulo'],
                descripcion=data.get('descripcion', ''),
                fecha_entrega=data['fecha_entrega']
            )

            return JsonResponse({'mensaje': 'Tarea creada exitosamente', 'id_tarea': tarea.id_tarea}, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class EditarTareaView(View):
    def put(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            id_tarea = kwargs.get('id_tarea')

            # Validar que los campos obligatorios estén presentes
            required_fields = ['id_criterio', 'titulo', 'fecha_entrega']
            for field in required_fields:
                if field not in data:
                    return JsonResponse({'error': f'El campo {field} es obligatorio'}, status=400)

            # Buscar la tarea por su ID
            tarea = Tarea.objects.filter(id_tarea=id_tarea).first()
            if not tarea:
                return JsonResponse({'error': 'Tarea no encontrada'}, status=404)

            # Actualizar los campos de la tarea
            tarea.id_criterio_id = data['id_criterio']
            tarea.titulo = data['titulo']
            tarea.descripcion = data.get('descripcion', tarea.descripcion)
            tarea.fecha_entrega = data['fecha_entrega']
            tarea.save()

            return JsonResponse({'mensaje': 'Tarea actualizada exitosamente', 'id_tarea': tarea.id_tarea}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class RegistrarCalificacionesView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            required_fields = ['id_tarea', 'calificaciones']  # calificaciones: lista de {id_persona, id_criterio, nota}

            for field in required_fields:
                if field not in data:
                    return JsonResponse({'error': f'El campo {field} es obligatorio'}, status=400)

            with transaction.atomic():
                for cal in data['calificaciones']:
                    calificacion, created = Calificacion.objects.update_or_create(
                        id_tarea_id=data['id_tarea'],
                        id_persona_id=cal['id_persona'],
                        defaults={'nota': cal['nota']}  
                    )
                    if created:
                        print(f"Calificación creada para {cal['id_persona']}")
                    else:
                        print(f"Calificación actualizada para {cal['id_persona']}")

            return JsonResponse({'mensaje': 'Calificaciones registradas correctamente'}, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ListarTareasCursoView(View):
    def get(self, request, *args, **kwargs):
        try:
            id_curso = kwargs.get('id_curso')
            tareas = Tarea.objects.filter(id_curso_id=id_curso).select_related('id_criterio')

            if not tareas:
                return JsonResponse({'error': 'No se encontraron tareas para este curso'}, status=404)

            tareas_data = []
            for tarea in tareas:
                tareas_data.append({
                    'id_tarea': tarea.id_tarea,
                    'titulo': tarea.titulo,
                    'descripcion': tarea.descripcion,
                    'fecha_entrega': tarea.fecha_entrega,
                    'id_criterio': tarea.id_criterio.nombre_criterio,  # Nombre del criterio
                    'porcentaje': tarea.id_criterio.porcentaje  # Porcentaje del criterio
                })

            return JsonResponse({'tareas': tareas_data}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class VerCalificacionesAlumnoView(View):
    def get(self, request, *args, **kwargs):
        try:
            id_persona = kwargs.get('id_persona')
            calificaciones = Calificacion.objects.filter(id_persona_id=id_persona).select_related('id_tarea', 'id_criterio')

            if not calificaciones:
                return JsonResponse({'error': 'No se encontraron calificaciones para este alumno'}, status=404)

            calificaciones_data = []
            for cal in calificaciones:
                calificaciones_data.append({
                    'id_tarea': cal.id_tarea.id_tarea,
                    'titulo_tarea': cal.id_tarea.titulo,
                    'criterio': cal.id_criterio.nombre_criterio,
                    'nota': cal.nota
                })

            return JsonResponse({'calificaciones': calificaciones_data}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
