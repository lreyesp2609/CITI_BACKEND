from django.http import JsonResponse
from django.views import View
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import jwt
import json
from datetime import datetime 
from .models import *
from django.conf import settings

@method_decorator(csrf_exempt, name='dispatch')
class CrearCursoView(View):
    def post(self, request, *args, **kwargs):
        try:
            # 1. Autenticación y validación de token
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

            # 2. Validación de campos obligatorios
            required_fields = ['nombre', 'descripcion', 'id_ciclo', 'fecha_inicio', 
                            'fecha_fin', 'hora_inicio', 'hora_fin']
            
            # Manejo tanto para form-data como para json
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST.dict()

            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return JsonResponse({
                    'error': f'Campos obligatorios faltantes: {", ".join(missing_fields)}'
                }, status=400)

            # 3. Validación de fechas
            try:
                fecha_inicio = datetime.strptime(data['fecha_inicio'], '%Y-%m-%d').date()
                fecha_fin = datetime.strptime(data['fecha_fin'], '%Y-%m-%d').date()
                
                if fecha_inicio > fecha_fin:
                    return JsonResponse({
                        'error': 'La fecha de inicio no puede ser posterior a la fecha fin'
                    }, status=400)
                    
            except ValueError:
                return JsonResponse({
                    'error': 'Formato de fecha inválido. Use YYYY-MM-DD'
                }, status=400)

            # 4. Validación de horas
            try:
                hora_inicio = datetime.strptime(data['hora_inicio'], '%H:%M').time()
                hora_fin = datetime.strptime(data['hora_fin'], '%H:%M').time()
                
                if hora_inicio >= hora_fin:
                    return JsonResponse({
                        'error': 'La hora de inicio debe ser anterior a la hora fin'
                    }, status=400)
                    
            except ValueError:
                return JsonResponse({
                    'error': 'Formato de hora inválido. Use HH:MM'
                }, status=400)

            # 5. Creación del curso con transacción atómica
            with transaction.atomic():
                # Crear el curso
                curso = Curso.objects.create(
                    nombre=data['nombre'],
                    descripcion=data['descripcion'],
                    id_ciclo_id=data['id_ciclo'],
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    id_usuario_id=id_usuario
                )

                # 6. Crear rúbrica por defecto
                criterios_por_defecto = [
                    {'nombre': 'Asistencia', 'porcentaje': Decimal('10.00')},
                    {'nombre': 'Actuación', 'porcentaje': Decimal('30.00')},
                    {'nombre': 'Tareas', 'porcentaje': Decimal('30.00')},
                    {'nombre': 'Examen', 'porcentaje': Decimal('30.00')},
                ]
                
                # Validar suma de porcentajes
                suma_porcentajes = sum(c['porcentaje'] for c in criterios_por_defecto)
                if suma_porcentajes != Decimal('100.00'):
                    raise ValueError(
                        f"La suma de porcentajes por defecto debe ser 100% (actual: {suma_porcentajes}%)"
                    )

                # Crear los criterios
                rubricas_creadas = []
                for criterio in criterios_por_defecto:
                    rubrica = Rubrica.objects.create(
                        id_curso=curso,
                        nombre_criterio=criterio['nombre'],
                        porcentaje=criterio['porcentaje']
                    )
                    rubricas_creadas.append({
                        'id_rubrica': rubrica.id_rubrica,
                        'nombre': rubrica.nombre_criterio,
                        'porcentaje': float(rubrica.porcentaje)  # Convertir a float para la respuesta JSON
                    })

                # 7. Preparar respuesta
                response_data = {
                    'mensaje': 'Curso creado exitosamente',
                    'id_curso': curso.id_curso,
                    'curso': {
                        'nombre': curso.nombre,
                        'fecha_inicio': curso.fecha_inicio.strftime('%Y-%m-%d'),
                        'fecha_fin': curso.fecha_fin.strftime('%Y-%m-%d'),
                    },
                    'rubricas_creadas': rubricas_creadas,
                    'total_rubricas': len(rubricas_creadas),
                    'suma_porcentajes': suma_porcentajes
                }

                return JsonResponse(response_data, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        
@method_decorator(csrf_exempt, name='dispatch')
class EditarCriteriosCursoView(View):
    def put(self, request, id_curso):
        try:
            # Verificar autenticación
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)
                
            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header
            
            try:
                jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            # Obtener datos del request
            data = json.loads(request.body)
            
            if 'criterios' not in data:
                return JsonResponse({'error': 'Se requiere la lista de criterios'}, status=400)
                
            criterios = data['criterios']
            
            # Validar estructura de los criterios
            for criterio in criterios:
                if 'id_rubrica' not in criterio or 'nombre_criterio' not in criterio or 'porcentaje' not in criterio:
                    return JsonResponse({'error': 'Cada criterio debe tener id_rubrica, nombre_criterio y porcentaje'}, status=400)
                
                try:
                    porcentaje = float(criterio['porcentaje'])
                    if porcentaje < 0 or porcentaje > 100:
                        raise ValueError
                except ValueError:
                    return JsonResponse({'error': 'Porcentaje debe ser un número entre 0 y 100'}, status=400)

            with transaction.atomic():
                # Verificar que el curso existe
                curso = Curso.objects.filter(id_curso=id_curso).first()
                if not curso:
                    return JsonResponse({'error': 'Curso no encontrado'}, status=404)
                
                # Validar que la suma de porcentajes sea 100%
                suma_porcentajes = sum(float(c['porcentaje']) for c in criterios)
                if round(suma_porcentajes, 2) != 100.00:
                    return JsonResponse({
                        'error': f'La suma de porcentajes debe ser exactamente 100% (actual: {suma_porcentajes}%)'
                    }, status=400)
                
                # Actualizar o crear criterios
                ids_procesados = []
                for criterio_data in criterios:
                    if criterio_data['id_rubrica']:  # Criterio existente
                        rubrica = Rubrica.objects.filter(
                            id_rubrica=criterio_data['id_rubrica'],
                            id_curso=curso
                        ).first()
                        
                        if not rubrica:
                            return JsonResponse({
                                'error': f'Criterio con ID {criterio_data["id_rubrica"]} no pertenece a este curso'
                            }, status=400)
                            
                        rubrica.nombre_criterio = criterio_data['nombre_criterio']
                        rubrica.porcentaje = criterio_data['porcentaje']
                        rubrica.save()
                        ids_procesados.append(rubrica.id_rubrica)
                    else:  # Nuevo criterio
                        rubrica = Rubrica.objects.create(
                            id_curso=curso,
                            nombre_criterio=criterio_data['nombre_criterio'],
                            porcentaje=criterio_data['porcentaje']
                        )
                        ids_procesados.append(rubrica.id_rubrica)
                
                # Eliminar criterios que no están en la lista enviada
                Rubrica.objects.filter(id_curso=curso).exclude(id_rubrica__in=ids_procesados).delete()
                
                return JsonResponse({
                    'mensaje': 'Criterios actualizados exitosamente',
                    'criterios_actualizados': len(ids_procesados)
                }, status=200)
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ListarCriteriosCursoView(View):
    def get(self, request, id_curso):
        try:
            criterios = Rubrica.objects.filter(id_curso_id=id_curso).values(
                'id_rubrica', 'nombre_criterio', 'porcentaje'
            )
            return JsonResponse(list(criterios), safe=False)
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

            # Verificar que el curso existe
            curso = Curso.objects.filter(id_curso=data['id_curso']).first()
            if not curso:
                return JsonResponse({'error': 'El curso no existe'}, status=404)

            # Verificar que el criterio pertenece al curso
            criterio = Rubrica.objects.filter(
                id_rubrica=data['id_criterio'],
                id_curso=curso
            ).first()
            
            if not criterio:
                return JsonResponse({'error': 'El criterio no pertenece a este curso'}, status=400)

            # Crear la tarea
            tarea = Tarea.objects.create(
                id_curso=curso,
                id_criterio=criterio,
                titulo=data['titulo'],
                descripcion=data.get('descripcion', ''),
                fecha_entrega=data['fecha_entrega']
            )

            return JsonResponse({
                'mensaje': 'Tarea creada exitosamente', 
                'id_tarea': tarea.id_tarea,
                'titulo': tarea.titulo,
                'criterio': criterio.nombre_criterio,
                'porcentaje': float(criterio.porcentaje)
            }, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class EditarTareaView(View):
    def put(self, request, id_tarea, *args, **kwargs):
        try:
            data = json.loads(request.body)
            required_fields = ['titulo', 'fecha_entrega', 'id_criterio']
            
            # Validar campos obligatorios
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return JsonResponse({
                    'error': f'Campos obligatorios faltantes: {", ".join(missing_fields)}'
                }, status=400)

            # Obtener la tarea existente
            tarea = Tarea.objects.filter(id_tarea=id_tarea).first()
            if not tarea:
                return JsonResponse({'error': 'Tarea no encontrada'}, status=404)

            # Verificar que el criterio pertenece al curso
            criterio = Rubrica.objects.filter(
                id_rubrica=data['id_criterio'],
                id_curso=tarea.id_curso
            ).first()
            
            if not criterio:
                return JsonResponse({
                    'error': 'El criterio no pertenece a este curso'
                }, status=400)

            # Actualizar la tarea
            tarea.titulo = data['titulo']
            tarea.descripcion = data.get('descripcion', tarea.descripcion)
            tarea.fecha_entrega = data['fecha_entrega']
            tarea.id_criterio = criterio
            tarea.save()

            return JsonResponse({
                'mensaje': 'Tarea actualizada exitosamente',
                'id_tarea': tarea.id_tarea,
                'titulo': tarea.titulo,
                'criterio': criterio.nombre_criterio,
                'porcentaje': float(criterio.porcentaje)
            }, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class VerTareaView(View):
    def get(self, request, *args, **kwargs):
        try:
            id_tarea = kwargs.get('id_tarea')
            if not id_tarea:
                return JsonResponse({'error': 'ID de tarea no proporcionado'}, status=400)
            
            tarea = Tarea.objects.filter(id_tarea=id_tarea).first()
            if not tarea:
                return JsonResponse({'error': 'Tarea no encontrada'}, status=404)
            
            tarea_data = {
                'id_tarea': tarea.id_tarea,
                'titulo': tarea.titulo,
                'descripcion': tarea.descripcion,
                'fecha_entrega': tarea.fecha_entrega.strftime('%Y-%m-%d') if tarea.fecha_entrega else None,
                'id_curso': {
                    'id_curso': tarea.id_curso.id_curso,
                    'nombre': tarea.id_curso.nombre
                },
                'id_criterio': {
                    'id_criterio': tarea.id_criterio.id_criterio,
                    'nombre': tarea.id_criterio.nombre
                }
            }
            
            return JsonResponse(tarea_data, status=200)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ListarTareasCursoView(View):
    def get(self, request, *args, **kwargs):
        try:
            id_curso = kwargs.get('id_curso')
            tareas = Tarea.objects.filter(id_curso_id=id_curso).select_related('id_criterio')

            tareas_data = []
            for tarea in tareas:
                tareas_data.append({
                    'id_tarea': tarea.id_tarea,
                    'titulo': tarea.titulo,
                    'descripcion': tarea.descripcion,
                    'fecha_entrega': tarea.fecha_entrega,
                    'id_criterio': tarea.id_criterio.id_rubrica, 
                    'criterio': tarea.id_criterio.nombre_criterio,  # Nombre del criterio
                    'porcentaje': tarea.id_criterio.porcentaje  # Porcentaje del criterio
                })

            return JsonResponse({'tareas': tareas_data}, status=200)

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
class ListarCalificacionesTareaView(View):
    def get(self, request, id_tarea, *args, **kwargs):
        try:
            # Verificar que la tarea existe
            tarea = Tarea.objects.get(id_tarea=id_tarea)
            
            # Obtener todos los participantes del curso con sus datos de persona
            participantes = CursoParticipante.objects.filter(
                id_curso=tarea.id_curso
            ).select_related('id_persona')
            
            # Obtener calificaciones existentes para esta tarea
            calificaciones = Calificacion.objects.filter(
                id_tarea=id_tarea
            ).select_related('id_persona')
            
            # Crear un diccionario de calificaciones por persona
            calificaciones_dict = {
                cal.id_persona.id_persona: cal.nota 
                for cal in calificaciones
            }
            
            # Preparar la respuesta
            resultado = []
            for participante in participantes:
                persona = participante.id_persona
                resultado.append({
                    'id_persona': persona.id_persona,
                    'nombres': persona.nombres,
                    'apellidos': persona.apellidos,
                    'nota': calificaciones_dict.get(persona.id_persona, None)
                })
            
            return JsonResponse({'participantes': resultado}, status=200)
            
        except Tarea.DoesNotExist:
            return JsonResponse({'error': 'La tarea no existe'}, status=404)
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
