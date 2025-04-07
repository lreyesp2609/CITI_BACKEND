from django.shortcuts import render
from Ministerio.models import Ministerio
import jwt
from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from Login.models import Persona, Rol, Usuario
from datetime import datetime

@method_decorator(csrf_exempt, name='dispatch')
class ListarPersonasView(View):
    def get(self, request, *args, **kwargs):
        try:
            # Obtener token del encabezado Authorization
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)
                
            # Extraer el token si viene con el prefijo Bearer
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            else:
                token = auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                rol_usuario = payload.get('rol')
                
                # Verificar si el rol está permitido (solo roles 1 y 2)
                rol_id = Rol.objects.filter(rol=rol_usuario).first()
                if not rol_id or rol_id.id_rol not in [1, 2]:
                    return JsonResponse({'error': 'No tiene permisos para ver la lista de personas'}, status=403)
                    
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)
            
            # Obtener todas las personas
            personas = Persona.objects.all().order_by('id_persona')            
            
            # Convertir a lista de diccionarios para la respuesta JSON
            personas_list = []
            for persona in personas:
                personas_list.append({
                    'id_persona': persona.id_persona,
                    'numero_cedula': persona.numero_cedula,
                    'nombres': persona.nombres,
                    'apellidos': persona.apellidos,
                    'fecha_nacimiento': persona.fecha_nacimiento.strftime('%Y-%m-%d') if persona.fecha_nacimiento else None,
                    'genero': persona.genero,
                    'celular': persona.celular,
                    'direccion': persona.direccion,
                    'correo_electronico': persona.correo_electronico,
                    'nivel_estudio': persona.nivel_estudio,
                    'nacionalidad': persona.nacionalidad,
                    'profesion': persona.profesion,
                    'estado_civil': persona.estado_civil,
                    'lugar_trabajo': persona.lugar_trabajo
                })
            
            return JsonResponse({'personas': personas_list}, status=200)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ListarPersonasConUsuarioView(View):
    def get(self, request, *args, **kwargs):
        try:
            # Verificación del token (igual que antes)
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)
                
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            else:
                token = auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                rol_usuario = payload.get('rol')
                
                rol_id = Rol.objects.filter(rol=rol_usuario).first()
                if not rol_id or rol_id.id_rol not in [1, 2]:
                    return JsonResponse({'error': 'No tiene permisos para ver la lista de personas'}, status=403)
                    
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)
            
            # Obtener todos los usuarios con sus personas relacionadas
            usuarios = Usuario.objects.select_related('id_persona', 'id_rol').all()
            
            # Pre-cargar todos los ministerios para optimización
            ministerios = Ministerio.objects.select_related('id_lider1', 'id_lider2').all()
            
            # Construir un diccionario de ministerios por usuario
            ministerios_por_usuario = {}
            for ministerio in ministerios:
                if ministerio.id_lider1:
                    if ministerio.id_lider1.id_usuario not in ministerios_por_usuario:
                        ministerios_por_usuario[ministerio.id_lider1.id_usuario] = []
                    ministerios_por_usuario[ministerio.id_lider1.id_usuario].append({
                        'id_ministerio': ministerio.id_ministerio,
                        'nombre': ministerio.nombre,
                        'descripcion': ministerio.descripcion,
                        'estado': ministerio.estado,
                        'rol_lider': 'Líder 1'
                    })
                
                if ministerio.id_lider2:
                    if ministerio.id_lider2.id_usuario not in ministerios_por_usuario:
                        ministerios_por_usuario[ministerio.id_lider2.id_usuario] = []
                    ministerios_por_usuario[ministerio.id_lider2.id_usuario].append({
                        'id_ministerio': ministerio.id_ministerio,
                        'nombre': ministerio.nombre,
                        'descripcion': ministerio.descripcion,
                        'estado': ministerio.estado,
                        'rol_lider': 'Líder 2'
                    })
            
            # Construir la lista de personas con usuario y sus ministerios
            personas_list = []
            for usuario in usuarios:
                persona = usuario.id_persona
                ministerios_persona = ministerios_por_usuario.get(usuario.id_usuario, [])
                
                personas_list.append({
                    'id_persona': persona.id_persona,
                    'numero_cedula': persona.numero_cedula,
                    'nombres': persona.nombres,
                    'apellidos': persona.apellidos,
                    'fecha_nacimiento': persona.fecha_nacimiento.strftime('%Y-%m-%d') if persona.fecha_nacimiento else None,
                    'genero': persona.genero,
                    'celular': persona.celular,
                    'direccion': persona.direccion,
                    'correo_electronico': persona.correo_electronico,
                    'nivel_estudio': persona.nivel_estudio,
                    'nacionalidad': persona.nacionalidad,
                    'profesion': persona.profesion,
                    'estado_civil': persona.estado_civil,
                    'lugar_trabajo': persona.lugar_trabajo,
                    'usuario': {
                        'id_usuario': usuario.id_usuario,
                        'nombre_usuario': usuario.usuario,
                        'rol': usuario.id_rol.rol,
                        'activo': usuario.activo
                    },
                    'ministerios': ministerios_persona
                })
            
            # Ordenar por id_persona
            personas_list.sort(key=lambda x: x['id_persona'])
            
            return JsonResponse({'personas_con_usuario': personas_list}, status=200)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        
@method_decorator(csrf_exempt, name='dispatch')
class DetallePersonaView(View):
    def get(self, request, id_persona, *args, **kwargs):
        try:
            # Obtener token del encabezado Authorization
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)
                
            # Extraer el token si viene con el prefijo Bearer
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            else:
                token = auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                rol_usuario = payload.get('rol')
                
                # Verificar si el rol está permitido (solo roles 1 y 2)
                rol_id = Rol.objects.filter(rol=rol_usuario).first()
                if not rol_id or rol_id.id_rol not in [1, 2]:
                    return JsonResponse({'error': 'No tiene permisos para ver detalles de personas'}, status=403)
                    
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)
            
            # Obtener la persona específica
            try:
                persona = Persona.objects.get(id_persona=id_persona)

                # Obtener el usuario relacionado y su rol
                usuario = Usuario.objects.filter(id_persona=persona).first()
                if usuario:
                    rol = usuario.id_rol.rol  # Obtener el nombre del rol
                else:
                    rol = "Miembro"  # Si no tiene usuario asociado, asignamos "Miembro" por defecto
                
                # Convertir a diccionario para la respuesta JSON
                persona_data = {
                    'id_persona': persona.id_persona,
                    'numero_cedula': persona.numero_cedula,
                    'nombres': persona.nombres,
                    'apellidos': persona.apellidos,
                    'fecha_nacimiento': persona.fecha_nacimiento.strftime('%Y-%m-%d') if persona.fecha_nacimiento else None,
                    'genero': persona.genero,
                    'celular': persona.celular,
                    'direccion': persona.direccion,
                    'correo_electronico': persona.correo_electronico,
                    'nivel_estudio': persona.nivel_estudio,
                    'nacionalidad': persona.nacionalidad,
                    'profesion': persona.profesion,
                    'estado_civil': persona.estado_civil,
                    'lugar_trabajo': persona.lugar_trabajo,
                    'rol': rol
                }
                
                return JsonResponse({'persona': persona_data}, status=200)
                
            except Persona.DoesNotExist:
                return JsonResponse({'error': 'Persona no encontrada'}, status=404)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ActualizarPersonaView(View):
    def post(self, request, id_persona, *args, **kwargs):
        try:
            # Obtener token del encabezado Authorization
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)
                
            # Extraer el token si viene con el prefijo Bearer
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            else:
                token = auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                rol_usuario = payload.get('rol')
                
                # Verificar si el rol está permitido (solo roles 1 y 2)
                rol_id = Rol.objects.filter(rol=rol_usuario).first()
                if not rol_id or rol_id.id_rol not in [1, 2]:
                    return JsonResponse({'error': 'No tiene permisos para actualizar personas'}, status=403)
                    
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)
            
            # Iniciar transacción
            from django.db import transaction
            with transaction.atomic():
                try:
                    persona = Persona.objects.get(id_persona=id_persona)
                except Persona.DoesNotExist:
                    return JsonResponse({'error': 'Persona no encontrada'}, status=404)
                
                # Verificar si hay al menos un campo para actualizar
                if not request.POST:
                    return JsonResponse({'error': 'No se proporcionaron datos para actualizar'}, status=400)
                
                # Verificar si se está actualizando la cédula y si ya existe
                numero_cedula = request.POST.get('numero_cedula')
                if numero_cedula:
                    # Verificar que la cédula no exista en otra persona
                    if Persona.objects.filter(numero_cedula=numero_cedula).exclude(id_persona=id_persona).exists():
                        return JsonResponse({'error': 'Ya existe otra persona con este número de cédula'}, status=400)
                    persona.numero_cedula = numero_cedula
                
                # Actualizar campos si están presentes
                if 'nombres' in request.POST and request.POST.get('nombres'):
                    persona.nombres = request.POST.get('nombres')
                
                if 'apellidos' in request.POST and request.POST.get('apellidos'):
                    persona.apellidos = request.POST.get('apellidos')
                
                # Actualizar campos opcionales si están presentes
                if 'fecha_nacimiento' in request.POST:
                    fecha_str = request.POST.get('fecha_nacimiento')
                    persona.fecha_nacimiento = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else None
                if 'genero' in request.POST:
                    persona.genero = request.POST.get('genero')
                if 'celular' in request.POST:
                    persona.celular = request.POST.get('celular')
                if 'direccion' in request.POST:
                    persona.direccion = request.POST.get('direccion')
                if 'correo_electronico' in request.POST:
                    persona.correo_electronico = request.POST.get('correo_electronico')
                if 'nivel_estudio' in request.POST:
                    persona.nivel_estudio = request.POST.get('nivel_estudio')
                if 'nacionalidad' in request.POST:
                    persona.nacionalidad = request.POST.get('nacionalidad')
                if 'profesion' in request.POST:
                    persona.profesion = request.POST.get('profesion')
                if 'estado_civil' in request.POST:
                    persona.estado_civil = request.POST.get('estado_civil')
                if 'lugar_trabajo' in request.POST:
                    persona.lugar_trabajo = request.POST.get('lugar_trabajo')
                
                # Guardar los cambios
                persona.save()
                
                # Preparar respuesta
                persona_data = {
                    'id_persona': persona.id_persona,
                    'numero_cedula': persona.numero_cedula,
                    'nombres': persona.nombres,
                    'apellidos': persona.apellidos,
                    'fecha_nacimiento': persona.fecha_nacimiento.strftime('%Y-%m-%d') if persona.fecha_nacimiento else None,
                    'genero': persona.genero,
                    'celular': persona.celular,
                    'direccion': persona.direccion,
                    'correo_electronico': persona.correo_electronico,
                    'nivel_estudio': persona.nivel_estudio,
                    'nacionalidad': persona.nacionalidad,
                    'profesion': persona.profesion,
                    'estado_civil': persona.estado_civil,
                    'lugar_trabajo': persona.lugar_trabajo
                }
                
                return JsonResponse({
                    'mensaje': 'Persona actualizada exitosamente',
                    'persona': persona_data
                }, status=200)
                
        except Exception as e:
            # Si ocurre cualquier error, la transacción hace rollback automáticamente
            return JsonResponse({'error': str(e)}, status=500)