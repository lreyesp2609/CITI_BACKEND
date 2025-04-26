import os
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

import os
import jwt
import traceback
from django.db import transaction
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.hashers import make_password

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
                id_usuario_actual = payload.get('id_usuario')
                
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

            # 4. Procesar la imagen si existe
            imagen_path = request.FILES.get('imagen')  # O request.FILES.get('imagen_path') según cómo envíes el archivo
            if imagen_path:
                # Validar tamaño de imagen (máximo 5MB)
                if imagen_path.size > 5 * 1024 * 1024:
                    return JsonResponse({'error': 'La imagen es demasiado grande (máximo 5MB)'}, status=400)
                
                # Validar tipo de archivo
                valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
                ext = os.path.splitext(imagen_path.name)[1].lower()
                if ext not in valid_extensions:
                    return JsonResponse({'error': 'Formato de imagen no válido. Use JPG, JPEG, PNG o WEBP'}, status=400)

            # 5. Procesar otros datos del formulario
            descripcion = request.POST.get('descripcion')
            estado = request.POST.get('estado', 'Activo')
            persona_lider1_id = request.POST.get('id_persona_lider1')
            persona_lider2_id = request.POST.get('id_persona_lider2')

            with transaction.atomic():
                # 6. Validar y convertir personas a líderes
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

                # 7. Crear ministerio (incluyendo la imagen)
                ministerio = Ministerio(
                    nombre=nombre_ministerio,
                    descripcion=descripcion,
                    estado=estado,
                    id_lider1=lider1,
                    id_lider2=lider2
                )
                
                # Asignar la imagen si existe
                if imagen_path:
                    ministerio.imagen_path = imagen_path
                
                ministerio.save()

                # Preparar URL de la imagen para la respuesta
                imagen_url = ministerio.imagen_path.url if ministerio.imagen_path else None

                response_data = {
                    'mensaje': 'Ministerio creado con éxito',
                    'id_ministerio': ministerio.id_ministerio,
                    'ministerio': nombre_ministerio,
                    'imagen_url': imagen_url,
                    'estado': estado
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

            # 2. Obtener todos los ministerios con información de líderes
            ministerios = Ministerio.objects.select_related(
                'id_lider1__id_persona', 
                'id_lider2__id_persona'
            ).all().order_by('id_ministerio')

            # 3. Preparar la respuesta
            ministerios_data = []
            for ministerio in ministerios:
                # Información del primer líder
                lider1_data = None
                if ministerio.id_lider1:
                    lider1_data = {
                        'id_persona': ministerio.id_lider1.id_persona.id_persona,
                        'id_usuario': ministerio.id_lider1.id_usuario,
                        'nombres': ministerio.id_lider1.id_persona.nombres,
                        'apellidos': ministerio.id_lider1.id_persona.apellidos,
                        'cedula': ministerio.id_lider1.id_persona.numero_cedula
                    }

                # Información del segundo líder
                lider2_data = None
                if ministerio.id_lider2:
                    lider2_data = {
                        'id_persona': ministerio.id_lider2.id_persona.id_persona,
                        'id_usuario': ministerio.id_lider2.id_usuario,
                        'nombres': ministerio.id_lider2.id_persona.nombres,
                        'apellidos': ministerio.id_lider2.id_persona.apellidos,
                        'cedula': ministerio.id_lider2.id_persona.numero_cedula
                    }

                # Obtener URL de la imagen si existe
                imagen_url = None
                if ministerio.imagen_path:
                    imagen_url = request.build_absolute_uri(ministerio.imagen_path.url)

                ministerios_data.append({
                    'id_ministerio': ministerio.id_ministerio,
                    'nombre': ministerio.nombre,
                    'descripcion': ministerio.descripcion,
                    'estado': ministerio.estado,
                    'imagen_url': imagen_url,  # Añadimos la URL de la imagen
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
                id_usuario_actual = payload.get('id_usuario')
                
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
            eliminar_imagen = request.POST.get('eliminar_imagen', 'false').lower() == 'true'
            imagen = request.FILES.get('imagen')
            
            # Bandera para indicar si la imagen fue modificada
            imagen_modificada = False

            with transaction.atomic():
                # 4. Manejo de la imagen
                if eliminar_imagen and ministerio.imagen_path:
                    # Eliminar el archivo físico si existe
                    if os.path.isfile(ministerio.imagen_path.path):
                        try:
                            os.remove(ministerio.imagen_path.path)
                        except OSError as e:
                            print(f"Error al eliminar imagen: {e}")
                    
                    ministerio.imagen_path = None
                    imagen_modificada = True
                
                if imagen:
                    # Validar tamaño de imagen (máximo 5MB)
                    if imagen.size > 5 * 1024 * 1024:
                        return JsonResponse({'error': 'La imagen es demasiado grande (máximo 5MB)'}, status=400)
                    
                    # Validar tipo de archivo
                    valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
                    ext = os.path.splitext(imagen.name)[1].lower()
                    if ext not in valid_extensions:
                        return JsonResponse({'error': 'Formato de imagen no válido. Use JPG, JPEG, PNG o WEBP'}, status=400)
                    
                    # Eliminar la imagen anterior si existe
                    if ministerio.imagen_path and os.path.isfile(ministerio.imagen_path.path):
                        try:
                            os.remove(ministerio.imagen_path.path)
                        except OSError as e:
                            print(f"Error al eliminar imagen anterior: {e}")
                    
                    ministerio.imagen_path = imagen
                    imagen_modificada = True

                # 5. Manejo de líderes actuales (para desactivar si son reemplazados)
                lideres_originales = {
                    'lider1': ministerio.id_lider1,
                    'lider2': ministerio.id_lider2
                }
                
                # 6. Función para manejar cambios de líderes
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

                # 7. Procesar nuevos líderes
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

                # 8. Validar que no sean la misma persona
                if (nuevos_lideres.get('lider1') and nuevos_lideres.get('lider2') and 
                    nuevos_lideres['lider1'].id_persona.id_persona == nuevos_lideres['lider2'].id_persona.id_persona):
                    return JsonResponse({'error': 'Una persona no puede ser ambos líderes'}, status=400)

                # 9. Desactivar líderes anteriores si fueron reemplazados
                for rol, lider_original in lideres_originales.items():
                    if lider_original and (rol in nuevos_lideres and nuevos_lideres[rol] != lider_original):
                        # Verificar si el líder original ya no es líder en otro ministerio
                        es_lider_en_otros = Ministerio.objects.filter(
                            Q(id_lider1=lider_original) | Q(id_lider2=lider_original)
                        ).exclude(id_ministerio=id_ministerio).exists()
                        
                        if not es_lider_en_otros:
                            lider_original.activo = False
                            lider_original.save()

                # 10. Actualizar ministerio
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

                # 11. Preparar respuesta
                response_data = {
                    'mensaje': 'Ministerio actualizado con éxito',
                    'id_ministerio': ministerio.id_ministerio,
                    'ministerio': ministerio.nombre,
                    'imagen_url': ministerio.imagen_path.url if ministerio.imagen_path else None,
                    'cambios': {
                        'nombre': nombre is not None,
                        'descripcion': descripcion is not None,
                        'estado': estado is not None,
                        'lider1': nuevo_lider1_id is not None,
                        'lider2': nuevo_lider2_id is not None,
                        'imagen': imagen_modificada
                    }
                }

                return JsonResponse(response_data, status=200)

        except Exception as e:
            error_trace = traceback.format_exc()
            return JsonResponse({'error': str(e), 'detalle': error_trace}, status=500)
        
def obtener_usuario_id(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        raise Exception('Token no proporcionado')
    
    token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
    return payload.get('id_usuario')

@method_decorator(csrf_exempt, name='dispatch')
class ListarMinisteriosUsuarioView(View):
    def get(self, request, usuario_id, *args, **kwargs):
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

            # 2. Obtener todos los ministerios del usuario (como líder1 o líder2)
            ministerios = Ministerio.objects.select_related(
                'id_lider1__id_persona', 
                'id_lider2__id_persona'
            ).filter(
                Q(id_lider1=usuario_id) | Q(id_lider2=usuario_id)
            ).order_by('id_ministerio')

            # 3. Preparar la respuesta
            ministerios_data = []
            for ministerio in ministerios:
                # Información del primer líder
                lider1_data = None
                if ministerio.id_lider1:
                    lider1_data = {
                        'id_persona': ministerio.id_lider1.id_persona.id_persona,
                        'id_usuario': ministerio.id_lider1.id_usuario,
                        'nombres': ministerio.id_lider1.id_persona.nombres,
                        'apellidos': ministerio.id_lider1.id_persona.apellidos,
                        'cedula': ministerio.id_lider1.id_persona.numero_cedula
                    }

                # Información del segundo líder
                lider2_data = None
                if ministerio.id_lider2:
                    lider2_data = {
                        'id_persona': ministerio.id_lider2.id_persona.id_persona,
                        'id_usuario': ministerio.id_lider2.id_usuario,
                        'nombres': ministerio.id_lider2.id_persona.nombres,
                        'apellidos': ministerio.id_lider2.id_persona.apellidos,
                        'cedula': ministerio.id_lider2.id_persona.numero_cedula
                    }

                # Obtener URL de la imagen si existe
                imagen_url = None
                if ministerio.imagen_path:
                    imagen_url = request.build_absolute_uri(ministerio.imagen_path.url)

                ministerios_data.append({
                    'id_ministerio': ministerio.id_ministerio,
                    'nombre': ministerio.nombre,
                    'descripcion': ministerio.descripcion,
                    'estado': ministerio.estado,
                    'imagen_url': imagen_url,
                    'lider1': lider1_data,
                    'lider2': lider2_data,
                })

            return JsonResponse({'ministerios': ministerios_data}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)