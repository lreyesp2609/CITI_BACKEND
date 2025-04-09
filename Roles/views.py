from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.hashers import make_password
from django.db import transaction
import jwt
from django.conf import settings
import json
import traceback
from django.views.decorators.csrf import csrf_exempt
from Login.models import Persona, Rol, Usuario

@method_decorator(csrf_exempt, name='dispatch')
class AsignarPastoresView(View):
    def post(self, request, *args, **kwargs):
        try:
            # 1. Validación del token
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=401)
                
            token = auth_header.split('Bearer ')[1] if 'Bearer ' in auth_header else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                rol_usuario = payload.get('rol')
                
                # Solo administradores (rol 1) pueden asignar pastores
                rol_id = Rol.objects.filter(rol=rol_usuario).first()
                if not rol_id or rol_id.id_rol != 1:
                    return JsonResponse({'error': 'No tiene permisos para esta acción'}, status=403)
                    
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            # 2. Parsear el JSON del body
            try:
                data = json.loads(request.body)
                personas_ids = list(set(data.get('personas', [])))  # Eliminar duplicados
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Formato JSON inválido'}, status=400)

            # 3. Validaciones básicas
            if not personas_ids:
                return JsonResponse({'error': 'No se proporcionaron personas'}, status=400)

            # 4. Procesamiento en transacción (con rollback automático si falla)
            with transaction.atomic():
                rol_pastor = Rol.objects.get(id_rol=1)
                personas_asignadas = []
                personas_rechazadas = []

                # Procesar cada persona
                for persona_id in personas_ids:
                    try:
                        persona = Persona.objects.get(id_persona=persona_id)
                        
                        # Validación completa de datos
                        campos_requeridos = [
                            persona.numero_cedula,
                            persona.nombres,
                            persona.apellidos,
                            persona.fecha_nacimiento,
                            persona.genero,
                            persona.celular,
                            persona.direccion,
                            persona.correo_electronico,
                            persona.nivel_estudio,
                            persona.nacionalidad,
                            persona.profesion,
                            persona.estado_civil
                        ]
                        
                        if any(campo is None or campo == '' for campo in campos_requeridos):
                            raise ValueError('Todos los datos personales deben estar completos para ser pastor')
                        
                        # Generar username único
                        base_username = f"{persona.nombres.split()[0].lower()}.{persona.apellidos.split()[0].lower()}"
                        username = base_username
                        suffix = 1
                        
                        # Verificar si el username ya existe y generar uno único
                        while Usuario.objects.filter(usuario=username).exists():
                            username = f"{base_username}{suffix}"
                            suffix += 1
                        
                        password = make_password(persona.numero_cedula)
                        
                        # Crear o actualizar usuario
                        usuario, created = Usuario.objects.get_or_create(
                            id_persona=persona,
                            defaults={
                                'id_rol': rol_pastor,
                                'usuario': username,
                                'contrasenia': password,
                                'activo': True
                            }
                        )
                        
                        # Si el usuario ya existía pero tenía otro rol
                        if not created and usuario.id_rol != rol_pastor:
                            usuario.id_rol = rol_pastor
                            usuario.save()
                        
                        personas_asignadas.append({
                            'id_persona': persona.id_persona,
                            'nombres_completos': f"{persona.nombres} {persona.apellidos}",
                            'cedula': persona.numero_cedula,
                            'credenciales': {
                                'usuario': username,
                                'password': persona.numero_cedula,
                                'nota': 'La contraseña es el número de cédula'
                            }
                        })

                    except Persona.DoesNotExist:
                        personas_rechazadas.append({
                            'id_persona': persona_id,
                            'error': 'Persona no encontrada'
                        })
                    # En la sección donde manejas errores en AsignarPastoresView
                    except Exception as e:
                        persona_error = {
                            'id_persona': persona_id,
                            'nombre_completo': f"{persona.nombres} {persona.apellidos}" if persona else f"ID {persona_id}",
                            'error': str(e)
                        }
                        personas_rechazadas.append(persona_error)

                # 5. Preparar respuesta detallada
                response_data = {
                    'estado': 'completado' if personas_asignadas else 'parcial',
                    'pastores_asignados': len(personas_asignadas),
                    'detalle_asignados': personas_asignadas,
                    'personas_rechazadas': personas_rechazadas if personas_rechazadas else None
                }

                status_code = 201 if personas_asignadas else 400 if not personas_rechazadas else 207
                return JsonResponse(response_data, status=status_code)

        except Exception as e:
            return JsonResponse({
                'error': 'Error interno del servidor',
                'detalle': str(e),
                'trace': traceback.format_exc()
            }, status=500)