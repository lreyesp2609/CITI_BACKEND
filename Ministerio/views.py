from django.shortcuts import render
import jwt
from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from Login.models import Persona, Usuario, Rol
from Ministerio.models import Ministerio
from django.db import transaction
from django.contrib.auth.hashers import make_password
import traceback
from django.db.models import Q 

@method_decorator(csrf_exempt, name='dispatch')
class CrearMinisterioView(View):
    def post(self, request, *args, **kwargs):
        try:
            # 1. Validación del token
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)
                
            token = auth_header.split('Bearer ')[1] if 'Bearer ' in auth_header else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                rol_usuario = payload.get('rol')
                id_usuario_actual = payload.get('id_usuario')  # Necesitamos el ID del usuario actual
                
                rol_id = Rol.objects.filter(rol=rol_usuario).first()
                if not rol_id or rol_id.id_rol not in [1, 2]:
                    return JsonResponse({'error': 'No tiene permisos para crear ministerios'}, status=403)
                    
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            # 2. Validar campos obligatorios
            nombre_ministerio = request.POST.get('nombre')
            if not nombre_ministerio:
                return JsonResponse({'error': 'El nombre del ministerio es obligatorio'}, status=400)

            # 3. Validar que no exista un ministerio con el mismo nombre
            if Ministerio.objects.filter(nombre__iexact=nombre_ministerio).exists():
                return JsonResponse({'error': 'Ya existe un ministerio con este nombre'}, status=400)

            # 4. Procesar formdata
            descripcion = request.POST.get('descripcion')
            estado = request.POST.get('estado', 'Activo')
            persona_lider1_id = request.POST.get('id_persona_lider1')
            persona_lider2_id = request.POST.get('id_persona_lider2')

            with transaction.atomic():
                # 5. Validar y convertir personas a líderes
                lider1 = lider2 = None
                usuarios_creados = {}
                rol_lider = Rol.objects.filter(id_rol=2).first()
                
                if not rol_lider:
                    return JsonResponse({'error': 'Rol de líder no configurado'}, status=400)

                # Obtener el usuario actual si existe
                usuario_actual = None
                if id_usuario_actual:
                    try:
                        usuario_actual = Usuario.objects.get(id_usuario=id_usuario_actual)
                    except Usuario.DoesNotExist:
                        pass

                # Función para crear/actualizar usuario líder
                def crear_actualizar_usuario_lider(persona_id):
                    try:
                        persona = Persona.objects.get(id_persona=int(persona_id))
                        
                        # Validar campos requeridos
                        campos_requeridos = [
                            persona.numero_cedula,
                            persona.fecha_nacimiento,
                            persona.genero,
                            persona.celular,
                            persona.direccion,
                            persona.correo_electronico,
                            persona.nivel_estudio,
                            persona.nacionalidad,
                            persona.profesion,
                            persona.estado_civil,
                            persona.lugar_trabajo
                        ]
                        
                        if any(campo is None or campo == '' for campo in campos_requeridos):
                            raise ValueError('Todos los datos de la persona deben estar completos para ser líder')
                        
                        # Buscar usuario existente para esta persona
                        usuario_existente = Usuario.objects.filter(id_persona=persona).first()
                        
                        if usuario_existente:
                            # Si ya existe usuario
                            rol_a_asignar = usuario_existente.id_rol
                            
                            # Verificar si es el usuario actual (Pastor)
                            if usuario_actual and usuario_actual.id_persona.id_persona == persona.id_persona:
                                # Mantener el rol actual (Pastor)
                                rol_a_asignar = usuario_actual.id_rol
                            else:
                                # Si no es Pastor, asignar rol de líder (si no es ya Pastor)
                                if usuario_existente.id_rol.id_rol != 1:
                                    rol_a_asignar = rol_lider
                            
                            # Actualizar usuario existente
                            usuario_existente.id_rol = rol_a_asignar
                            usuario_existente.activo = True
                            usuario_existente.save()
                            
                            return usuario_existente
                        else:
                            # Crear nuevo usuario
                            primer_nombre = persona.nombres.split()[0].lower()
                            primer_apellido = persona.apellidos.split()[0].lower()
                            base_username = f"{primer_nombre}.{primer_apellido}"
                            password = make_password(persona.numero_cedula)
                            
                            # Determinar rol (2 por defecto, 1 si es el usuario actual Pastor)
                            rol_a_asignar = rol_lider
                            if usuario_actual and usuario_actual.id_persona.id_persona == persona.id_persona:
                                rol_a_asignar = usuario_actual.id_rol
                            
                            # Generar username único
                            username = base_username
                            counter = 1
                            while Usuario.objects.filter(usuario=username).exists():
                                username = f"{base_username}{counter}"
                                counter += 1
                            
                            # Crear usuario
                            usuario = Usuario.objects.create(
                                id_persona=persona,
                                id_rol=rol_a_asignar,
                                usuario=username,
                                contrasenia=password,
                                activo=True
                            )
                            
                            return usuario
                    
                    except Persona.DoesNotExist:
                        raise ValueError('Persona no encontrada')
                    except Exception as e:
                        raise ValueError(str(e))

                # Procesar primer líder
                if persona_lider1_id:
                    try:
                        lider1 = crear_actualizar_usuario_lider(persona_lider1_id)
                        usuarios_creados['lider1'] = {
                            'id_usuario': lider1.id_usuario,
                            'usuario': lider1.usuario,
                            'id_persona': lider1.id_persona.id_persona,
                            'rol': lider1.id_rol.rol
                        }
                    except ValueError as e:
                        return JsonResponse({'error': f'Líder 1 no válido: {str(e)}'}, status=400)

                # Procesar segundo líder
                if persona_lider2_id:
                    try:
                        if persona_lider1_id and int(persona_lider2_id) == int(persona_lider1_id):
                            return JsonResponse({'error': 'Una persona no puede ser ambos líderes'}, status=400)
                        
                        lider2 = crear_actualizar_usuario_lider(persona_lider2_id)
                        usuarios_creados['lider2'] = {
                            'id_usuario': lider2.id_usuario,
                            'usuario': lider2.usuario,
                            'id_persona': lider2.id_persona.id_persona,
                            'rol': lider2.id_rol.rol
                        }
                    except ValueError as e:
                        return JsonResponse({'error': f'Líder 2 no válido: {str(e)}'}, status=400)

                # 6. Crear ministerio
                ministerio = Ministerio.objects.create(
                    nombre=nombre_ministerio,
                    descripcion=descripcion,
                    estado=estado,
                    id_lider1=lider1,
                    id_lider2=lider2
                )

                response_data = {
                    'mensaje': 'Ministerio creado con éxito',
                    'id_ministerio': ministerio.id_ministerio,
                    'ministerio': nombre_ministerio,
                }
                
                if usuarios_creados:
                    response_data['lideres'] = usuarios_creados

                return JsonResponse(response_data, status=201)

        except Exception as e:
            error_trace = traceback.format_exc()
            return JsonResponse({'error': str(e), 'detalle': error_trace}, status=500)
        
@method_decorator(csrf_exempt, name='dispatch')
class ListarMinisteriosView(View):
    def get(self, request, *args, **kwargs):
        try:
            # 1. Validación del token
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)
                
            token = auth_header.split('Bearer ')[1] if 'Bearer ' in auth_header else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                rol_usuario = payload.get('rol')
                
                # Verificar permisos (puedes ajustar los roles permitidos)
                rol_id = Rol.objects.filter(rol=rol_usuario).first()
                if not rol_id:
                    return JsonResponse({'error': 'Rol no válido'}, status=403)
                    
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            # 2. Obtener todos los ministerios con información de líderes, ordenados por id_ministerio ascendente
            ministerios = Ministerio.objects.select_related(
                'id_lider1__id_persona', 
                'id_lider2__id_persona'
            ).all().order_by('id_ministerio')  # <- Aquí añades el order_by

            # 3. Preparar la respuesta
            ministerios_data = []
            for ministerio in ministerios:
                # Información del primer líder
                lider1_data = None
                if ministerio.id_lider1:
                    lider1_data = {
                        'id_usuario': ministerio.id_lider1.id_usuario,
                        'nombres': ministerio.id_lider1.id_persona.nombres,
                        'apellidos': ministerio.id_lider1.id_persona.apellidos,
                        'cedula': ministerio.id_lider1.id_persona.numero_cedula
                    }

                # Información del segundo líder
                lider2_data = None
                if ministerio.id_lider2:
                    lider2_data = {
                        'id_usuario': ministerio.id_lider2.id_usuario,
                        'nombres': ministerio.id_lider2.id_persona.nombres,
                        'apellidos': ministerio.id_lider2.id_persona.apellidos,
                        'cedula': ministerio.id_lider2.id_persona.numero_cedula
                    }

                ministerios_data.append({
                    'id_ministerio': ministerio.id_ministerio,
                    'nombre': ministerio.nombre,
                    'descripcion': ministerio.descripcion,
                    'estado': ministerio.estado,
                    'lider1': lider1_data,
                    'lider2': lider2_data,
                })

            return JsonResponse({'ministerios': ministerios_data}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        
@method_decorator(csrf_exempt, name='dispatch')
class EditarMinisterioView(View):
    def post(self, request, id_ministerio, *args, **kwargs):
        try:
            # 1. Validación del token
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)
                
            token = auth_header.split('Bearer ')[1] if 'Bearer ' in auth_header else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                rol_usuario = payload.get('rol')
                id_usuario_actual = payload.get('id_usuario')  # Necesitamos el ID del usuario actual
                
                rol_id = Rol.objects.filter(rol=rol_usuario).first()
                if not rol_id or rol_id.id_rol not in [1, 2]:
                    return JsonResponse({'error': 'No tiene permisos para editar ministerios'}, status=403)
                    
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            # 2. Obtener el ministerio a editar
            try:
                ministerio = Ministerio.objects.get(id_ministerio=id_ministerio)
            except Ministerio.DoesNotExist:
                return JsonResponse({'error': 'Ministerio no encontrado'}, status=404)

            # 3. Procesar datos del formulario
            nombre = request.POST.get('nombre')
            descripcion = request.POST.get('descripcion')
            estado = request.POST.get('estado')
            nuevo_lider1_id = request.POST.get('id_persona_lider1')
            nuevo_lider2_id = request.POST.get('id_persona_lider2')

            with transaction.atomic():
                # 4. Manejo de líderes actuales (para desactivar si son reemplazados)
                lideres_originales = {
                    'lider1': ministerio.id_lider1,
                    'lider2': ministerio.id_lider2
                }
                
                # 5. Función para manejar cambios de líderes
                def procesar_lider(persona_id, lider_actual, usuario_actual=None):
                    if not persona_id:
                        return None
                    
                    try:
                        persona = Persona.objects.get(id_persona=int(persona_id))
                        
                        # Validar campos requeridos para líder
                        campos_requeridos = [
                            persona.numero_cedula,
                            persona.fecha_nacimiento,
                            persona.genero,
                            persona.celular,
                            persona.direccion,
                            persona.correo_electronico,
                            persona.nivel_estudio,
                            persona.nacionalidad,
                            persona.profesion,
                            persona.estado_civil,
                            persona.lugar_trabajo
                        ]
                        
                        if any(campo is None or campo == '' for campo in campos_requeridos):
                            raise ValueError('Todos los datos de la persona deben estar completos para ser líder')
                        
                        # Buscar usuario existente para esta persona
                        usuario_existente = Usuario.objects.filter(id_persona=persona).first()
                        
                        if usuario_existente:
                            # Si ya existe un usuario para esta persona, lo actualizamos
                            rol_lider = Rol.objects.get(id_rol=2)
                            
                            # Verificar si el usuario actual (Pastor) está siendo asignado como líder
                            if usuario_actual and usuario_actual.id_persona.id_persona == persona.id_persona:
                                # Si el usuario actual es Pastor (rol 1), mantener su rol
                                rol_lider = usuario_actual.id_rol
                            
                            # Actualizar el usuario existente
                            if usuario_existente.id_rol.id_rol != 1:  # No cambiar el rol si ya es Pastor
                                usuario_existente.id_rol = rol_lider
                            usuario_existente.activo = True
                            usuario_existente.save()
                            
                            return usuario_existente
                        else:
                            # Si no existe usuario, crear uno nuevo con username único
                            rol_lider = Rol.objects.get(id_rol=2)
                            primer_nombre = persona.nombres.split()[0].lower()
                            primer_apellido = persona.apellidos.split()[0].lower()
                            base_username = f"{primer_nombre}.{primer_apellido}"
                            password = make_password(persona.numero_cedula)
                            
                            # Verificar si el usuario actual (Pastor) está siendo asignado como líder
                            if usuario_actual and usuario_actual.id_persona.id_persona == persona.id_persona:
                                # Si el usuario actual es Pastor (rol 1), mantener su rol
                                rol_lider = usuario_actual.id_rol
                            
                            # Generar username único
                            username = base_username
                            counter = 1
                            while Usuario.objects.filter(usuario=username).exists():
                                username = f"{base_username}{counter}"
                                counter += 1
                            
                            # Crear nuevo usuario
                            usuario = Usuario.objects.create(
                                id_persona=persona,
                                id_rol=rol_lider,
                                usuario=username,
                                contrasenia=password,
                                activo=True
                            )
                            
                            return usuario
                    
                    except Exception as e:
                        raise ValueError(str(e))

                # 6. Procesar nuevos líderes
                nuevos_lideres = {}
                errores = {}
                
                # Obtener el usuario actual si existe
                usuario_actual = None
                if id_usuario_actual:
                    try:
                        usuario_actual = Usuario.objects.get(id_usuario=id_usuario_actual)
                    except Usuario.DoesNotExist:
                        pass
                
                if nuevo_lider1_id is not None:  # None significa que no se envió, '' significa que se quiere quitar
                    try:
                        nuevos_lideres['lider1'] = procesar_lider(nuevo_lider1_id, lideres_originales['lider1'], usuario_actual) if nuevo_lider1_id != '' else None
                    except ValueError as e:
                        errores['lider1'] = str(e)

                if nuevo_lider2_id is not None:
                    try:
                        nuevos_lideres['lider2'] = procesar_lider(nuevo_lider2_id, lideres_originales['lider2'], usuario_actual) if nuevo_lider2_id != '' else None
                    except ValueError as e:
                        errores['lider2'] = str(e)

                if errores:
                    return JsonResponse({'error': 'Error en los líderes', 'detalles': errores}, status=400)

                # 7. Validar que no sean la misma persona
                if (nuevos_lideres.get('lider1') and nuevos_lideres.get('lider2') and 
                    nuevos_lideres['lider1'].id_persona.id_persona == nuevos_lideres['lider2'].id_persona.id_persona):
                    return JsonResponse({'error': 'Una persona no puede ser ambos líderes'}, status=400)

                # 8. Desactivar líderes anteriores si fueron reemplazados
                for rol, lider_original in lideres_originales.items():
                    if lider_original and (rol in nuevos_lideres and nuevos_lideres[rol] != lider_original):
                        # Verificar si el líder original ya no es líder en otro ministerio
                        es_lider_en_otros = Ministerio.objects.filter(
                            Q(id_lider1=lider_original) | Q(id_lider2=lider_original)
                        ).exclude(id_ministerio=id_ministerio).exists()
                        
                        if not es_lider_en_otros:
                            lider_original.activo = False
                            lider_original.save()

                # 9. Actualizar ministerio
                if nombre is not None and nombre != '':
                    # Verificar que el nuevo nombre no exista (excepto para este ministerio)
                    if Ministerio.objects.filter(nombre__iexact=nombre).exclude(id_ministerio=id_ministerio).exists():
                        return JsonResponse({'error': 'Ya existe un ministerio con este nombre'}, status=400)
                    ministerio.nombre = nombre
                
                if descripcion is not None:
                    ministerio.descripcion = descripcion
                
                if estado is not None and estado != '':
                    ministerio.estado = estado
                
                if 'lider1' in nuevos_lideres:
                    ministerio.id_lider1 = nuevos_lideres['lider1']
                
                if 'lider2' in nuevos_lideres:
                    ministerio.id_lider2 = nuevos_lideres['lider2']
                
                ministerio.save()

                # 10. Preparar respuesta
                response_data = {
                    'mensaje': 'Ministerio actualizado con éxito',
                    'id_ministerio': ministerio.id_ministerio,
                    'ministerio': ministerio.nombre,
                    'cambios': {
                        'nombre': nombre is not None,
                        'descripcion': descripcion is not None,
                        'estado': estado is not None,
                        'lider1': nuevo_lider1_id is not None,
                        'lider2': nuevo_lider2_id is not None
                    }
                }

                return JsonResponse(response_data, status=200)

        except Exception as e:
            error_trace = traceback.format_exc()
            return JsonResponse({'error': str(e), 'detalle': error_trace}, status=500)