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
from Ministerio.models import Ministerio
from django.db.models import Q

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
        

from django.db.models import Q

@method_decorator(csrf_exempt, name='dispatch')
class AsignarLideresMinisterioView(View):
    def post(self, request, *args, **kwargs):
        try:
            # 1. Validación del token (se mantiene igual)
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=401)
                
            token = auth_header.split('Bearer ')[1] if 'Bearer ' in auth_header else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                rol_usuario = payload.get('rol')
                
                # Solo administradores (rol 1) pueden asignar líderes
                rol_id = Rol.objects.filter(rol=rol_usuario).first()
                if not rol_id or rol_id.id_rol != 1:
                    return JsonResponse({'error': 'No tiene permisos para esta acción'}, status=403)
                    
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            # 2. Parsear los datos del formulario con validación adicional
            try:
                ministerio_id = request.POST.get('ministerio_id')
                lider1_id = request.POST.get('lider1_id')
                lider2_id = request.POST.get('lider2_id')
                
                if not ministerio_id:
                    return JsonResponse({'error': 'Ministerio no proporcionado'}, status=400)
                    
                if not lider1_id and not lider2_id:
                    return JsonResponse({'error': 'Debe proporcionar al menos un líder'}, status=400)
                    
                # Validar que no sea la misma persona para ambos roles
                if lider1_id and lider2_id and lider1_id == lider2_id:
                    return JsonResponse({'error': 'Una persona no puede ser líder 1 y líder 2 simultáneamente'}, status=400)

                # Verificar que las personas seleccionadas tengan sus datos completos
                if lider1_id:
                    persona1 = Persona.objects.get(id_persona=lider1_id)
                    if not self._validar_datos_completos(persona1):
                        return JsonResponse({
                            'error': 'Perfil incompleto', 
                            'detalle': f'La persona {persona1.nombres} {persona1.apellidos} no tiene todos sus datos completos para ser líder'
                        }, status=400)
                
                if lider2_id:
                    persona2 = Persona.objects.get(id_persona=lider2_id)
                    if not self._validar_datos_completos(persona2):
                        return JsonResponse({
                            'error': 'Perfil incompleto', 
                            'detalle': f'La persona {persona2.nombres} {persona2.apellidos} no tiene todos sus datos completos para ser líder'
                        }, status=400)

            except Persona.DoesNotExist:
                return JsonResponse({'error': 'Persona no encontrada'}, status=404)
            except Exception as e:
                return JsonResponse({'error': 'Error al procesar los datos del formulario', 'detalle': str(e)}, status=400)

            # 3. Procesamiento en transacción
            with transaction.atomic():
                try:
                    ministerio = Ministerio.objects.get(id_ministerio=ministerio_id)
                    usuarios_desactivados = []
                    cambios_realizados = False
                    
                    # Obtener los IDs actuales para comparar
                    lider1_actual_id = ministerio.id_lider1.id_persona.id_persona if ministerio.id_lider1 else None
                    lider2_actual_id = ministerio.id_lider2.id_persona.id_persona if ministerio.id_lider2 else None
                    
                    # CASO ESPECIAL: intercambio de líderes
                    intercambio = False
                    if (lider1_id and lider2_id and 
                        lider1_id == str(lider2_actual_id) and 
                        lider2_id == str(lider1_actual_id)):
                        intercambio = True
                        # Simplemente intercambiamos los líderes sin desactivar
                        temp = ministerio.id_lider1
                        ministerio.id_lider1 = ministerio.id_lider2
                        ministerio.id_lider2 = temp
                        ministerio.save()
                        cambios_realizados = True
                    
                    if not intercambio:
                        # Guardar usuarios actuales en variables temporales para evitar que se pierdan en el proceso
                        usuario_lider1_actual = ministerio.id_lider1
                        usuario_lider2_actual = ministerio.id_lider2
                        
                        # Procesar líder 1 si se proporcionó
                        if lider1_id:
                            # Verificar si el líder 1 actual está siendo movido a líder 2
                            mover_a_lider2 = lider1_actual_id and str(lider1_actual_id) == lider2_id
                            
                            if usuario_lider1_actual and not mover_a_lider2 and str(lider1_actual_id) != lider1_id:
                                # Verificar si el usuario es líder en algún otro ministerio antes de desactivarlo
                                otros_ministerios = Ministerio.objects.filter(
                                    Q(id_lider1=usuario_lider1_actual) | Q(id_lider2=usuario_lider1_actual)
                                ).exclude(id_ministerio=ministerio_id).count()
                                
                                if otros_ministerios == 0:
                                    # Solo desactivar si no es líder en ningún otro ministerio
                                    usuario_lider1_actual.activo = False
                                    usuario_lider1_actual.save()
                                    usuarios_desactivados.append({
                                        'id_usuario': usuario_lider1_actual.id_usuario,
                                        'usuario': usuario_lider1_actual.usuario,
                                        'motivo': 'Reemplazado como líder 1 y no es líder en otros ministerios'
                                    })
                                else:
                                    usuarios_desactivados.append({
                                        'id_usuario': usuario_lider1_actual.id_usuario,
                                        'usuario': usuario_lider1_actual.usuario,
                                        'motivo': 'Reemplazado como líder 1 pero sigue activo en otros ministerios'
                                    })
                            
                            # Asignar nuevo líder 1
                            persona_lider1 = Persona.objects.get(id_persona=lider1_id)
                            # Verificar si esta persona ya es un usuario
                            usuario_existente = Usuario.objects.filter(id_persona=persona_lider1).first()
                            
                            if usuario_existente:
                                # Si ya existe, asegurarse de que esté activo
                                usuario_existente.activo = True
                                usuario_existente.save()
                                ministerio.id_lider1 = usuario_existente
                            else:
                                # Crear nuevo usuario con rol de líder (2)
                                base_username = f"{persona_lider1.nombres.split()[0].lower()}.{persona_lider1.apellidos.split()[0].lower()}"
                                username = base_username
                                suffix = 1
                                
                                while Usuario.objects.filter(usuario=username).exists():
                                    username = f"{base_username}{suffix}"
                                    suffix += 1
                                
                                password = make_password(persona_lider1.numero_cedula)
                                
                                nuevo_usuario = Usuario.objects.create(
                                    id_rol=Rol.objects.get(id_rol=2),
                                    id_persona=persona_lider1,
                                    usuario=username,
                                    contrasenia=password,
                                    activo=True
                                )
                                ministerio.id_lider1 = nuevo_usuario
                            
                            cambios_realizados = True
                        else:
                            # Si no se proporciona líder 1, se elimina el actual
                            if usuario_lider1_actual:
                                # Verificar si el usuario es líder en algún otro ministerio antes de desactivarlo
                                otros_ministerios = Ministerio.objects.filter(
                                    Q(id_lider1=usuario_lider1_actual) | Q(id_lider2=usuario_lider1_actual)
                                ).exclude(id_ministerio=ministerio_id).count()
                                
                                if otros_ministerios == 0:
                                    # Solo desactivar si no es líder en ningún otro ministerio
                                    usuario_lider1_actual.activo = False
                                    usuario_lider1_actual.save()
                                    usuarios_desactivados.append({
                                        'id_usuario': usuario_lider1_actual.id_usuario,
                                        'usuario': usuario_lider1_actual.usuario,
                                        'motivo': 'Eliminado como líder 1 y no es líder en otros ministerios'
                                    })
                                else:
                                    usuarios_desactivados.append({
                                        'id_usuario': usuario_lider1_actual.id_usuario,
                                        'usuario': usuario_lider1_actual.usuario,
                                        'motivo': 'Eliminado como líder 1 pero sigue activo en otros ministerios'
                                    })
                                
                                ministerio.id_lider1 = None
                                cambios_realizados = True
                        
                        # Procesar líder 2 si se proporcionó
                        if lider2_id:
                            # Verificar si el líder 2 actual está siendo movido a líder 1
                            mover_a_lider1 = lider2_actual_id and str(lider2_actual_id) == lider1_id
                            
                            # Solo desactivar el líder 2 actual si no está siendo movido a líder 1
                            if usuario_lider2_actual and not mover_a_lider1 and str(lider2_actual_id) != lider2_id:
                                # Verificar si el usuario es líder en algún otro ministerio antes de desactivarlo
                                otros_ministerios = Ministerio.objects.filter(
                                    Q(id_lider1=usuario_lider2_actual) | Q(id_lider2=usuario_lider2_actual)
                                ).exclude(id_ministerio=ministerio_id).count()
                                
                                if otros_ministerios == 0:
                                    # Solo desactivar si no es líder en ningún otro ministerio
                                    usuario_lider2_actual.activo = False
                                    usuario_lider2_actual.save()
                                    usuarios_desactivados.append({
                                        'id_usuario': usuario_lider2_actual.id_usuario,
                                        'usuario': usuario_lider2_actual.usuario,
                                        'motivo': 'Reemplazado como líder 2 y no es líder en otros ministerios'
                                    })
                                else:
                                    usuarios_desactivados.append({
                                        'id_usuario': usuario_lider2_actual.id_usuario,
                                        'usuario': usuario_lider2_actual.usuario,
                                        'motivo': 'Reemplazado como líder 2 pero sigue activo en otros ministerios'
                                    })
                            
                            # Asignar nuevo líder 2
                            persona_lider2 = Persona.objects.get(id_persona=lider2_id)
                            # Verificar si esta persona ya es un usuario
                            usuario_existente = Usuario.objects.filter(id_persona=persona_lider2).first()
                            
                            if usuario_existente:
                                # Si ya existe, asegurarse de que esté activo
                                usuario_existente.activo = True
                                usuario_existente.save()
                                ministerio.id_lider2 = usuario_existente
                            else:
                                # Crear nuevo usuario con rol de líder (2)
                                base_username = f"{persona_lider2.nombres.split()[0].lower()}.{persona_lider2.apellidos.split()[0].lower()}"
                                username = base_username
                                suffix = 1
                                
                                while Usuario.objects.filter(usuario=username).exists():
                                    username = f"{base_username}{suffix}"
                                    suffix += 1
                                
                                password = make_password(persona_lider2.numero_cedula)
                                
                                nuevo_usuario = Usuario.objects.create(
                                    id_rol=Rol.objects.get(id_rol=2),
                                    id_persona=persona_lider2,
                                    usuario=username,
                                    contrasenia=password,
                                    activo=True
                                )
                                ministerio.id_lider2 = nuevo_usuario
                            
                            cambios_realizados = True
                        else:
                            # Si no se proporciona líder 2, se elimina el actual
                            if usuario_lider2_actual:
                                # Verificar si el usuario es líder en algún otro ministerio antes de desactivarlo
                                otros_ministerios = Ministerio.objects.filter(
                                    Q(id_lider1=usuario_lider2_actual) | Q(id_lider2=usuario_lider2_actual)
                                ).exclude(id_ministerio=ministerio_id).count()
                                
                                if otros_ministerios == 0:
                                    # Solo desactivar si no es líder en ningún otro ministerio
                                    usuario_lider2_actual.activo = False
                                    usuario_lider2_actual.save()
                                    usuarios_desactivados.append({
                                        'id_usuario': usuario_lider2_actual.id_usuario,
                                        'usuario': usuario_lider2_actual.usuario,
                                        'motivo': 'Eliminado como líder 2 y no es líder en otros ministerios'
                                    })
                                else:
                                    usuarios_desactivados.append({
                                        'id_usuario': usuario_lider2_actual.id_usuario,
                                        'usuario': usuario_lider2_actual.usuario,
                                        'motivo': 'Eliminado como líder 2 pero sigue activo en otros ministerios'
                                    })
                                
                                ministerio.id_lider2 = None
                                cambios_realizados = True
                    
                    # Guardar cambios en el ministerio si hubo modificaciones
                    if cambios_realizados:
                        ministerio.save()
                    
                    # Preparar respuesta
                    response_data = {
                        'estado': 'completado',
                        'ministerio_id': ministerio.id_ministerio,
                        'ministerio_nombre': ministerio.nombre,
                        'lider1_asignado': {
                            'id_persona': ministerio.id_lider1.id_persona.id_persona if ministerio.id_lider1 else None,
                            'nombres': ministerio.id_lider1.id_persona.nombres if ministerio.id_lider1 else None,
                            'apellidos': ministerio.id_lider1.id_persona.apellidos if ministerio.id_lider1 else None,
                            'rol': ministerio.id_lider1.id_rol.rol if ministerio.id_lider1 else None
                        } if ministerio.id_lider1 else None,
                        'lider2_asignado': {
                            'id_persona': ministerio.id_lider2.id_persona.id_persona if ministerio.id_lider2 else None,
                            'nombres': ministerio.id_lider2.id_persona.nombres if ministerio.id_lider2 else None,
                            'apellidos': ministerio.id_lider2.id_persona.apellidos if ministerio.id_lider2 else None,
                            'rol': ministerio.id_lider2.id_rol.rol if ministerio.id_lider2 else None
                        } if ministerio.id_lider2 else None,
                        'usuarios_desactivados': usuarios_desactivados if usuarios_desactivados else None
                    }
                    
                    return JsonResponse(response_data, status=200)
                
                except Ministerio.DoesNotExist:
                    return JsonResponse({'error': 'Ministerio no encontrado'}, status=404)
                except Persona.DoesNotExist as e:
                    return JsonResponse({'error': 'Persona no encontrada', 'detalle': str(e)}, status=404)
                except Exception as e:
                    return JsonResponse({'error': 'Error al procesar la asignación', 'detalle': str(e)}, status=400)

        except Exception as e:
            return JsonResponse({
                'error': 'Error interno del servidor',
                'detalle': str(e)
            }, status=500)
    
    def _validar_datos_completos(self, persona):
        """
        Verifica que todos los campos requeridos de una persona estén completos
        para poder ser asignada como líder.
        """
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
        
        # Verificar que ninguno de los campos esté vacío o sea None
        return all(campo for campo in campos_requeridos)