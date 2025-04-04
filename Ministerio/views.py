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
            # 1. Validación del token (igual que ListarPersonasView)
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)
                
            token = auth_header.split('Bearer ')[1] if 'Bearer ' in auth_header else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                rol_usuario = payload.get('rol')
                
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
            persona_lider1_id = request.POST.get('id_persona_lider1')  # Cambiado a id_persona
            persona_lider2_id = request.POST.get('id_persona_lider2')  # Cambiado a id_persona

            with transaction.atomic():
                # 5. Validar y convertir personas a líderes
                lider1 = lider2 = None
                usuarios_creados = {}
                rol_lider = Rol.objects.filter(id_rol=2).first()
                
                if not rol_lider:
                    return JsonResponse({'error': 'Rol de líder no configurado'}, status=400)

                # Función para crear usuario líder desde persona
                def crear_usuario_lider(persona_id):
                    try:
                        persona = Persona.objects.get(id_persona=int(persona_id))
                        
                        # Validar que todos los campos de la persona estén completos
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
                        
                        # Generar usuario y contraseña
                        primer_nombre = persona.nombres.split()[0].lower()
                        primer_apellido = persona.apellidos.split()[0].lower()
                        username = f"{primer_nombre}.{primer_apellido}"
                        password = make_password(persona.numero_cedula)
                        
                        # Crear usuario (si no existe)
                        usuario, created = Usuario.objects.get_or_create(
                            id_persona=persona,
                            defaults={
                                'id_rol': rol_lider,
                                'usuario': username,
                                'contrasenia': password,
                                'activo': True  # Asegurar que esté activo al crearse
                            }
                        )
                        
                        if not created:
                            # Si el usuario ya existe, actualizar a líder y asegurarse que esté activo
                            usuario.id_rol = rol_lider
                            usuario.activo = True
                            usuario.save()
                        
                        return usuario
                    
                    except Persona.DoesNotExist:
                        raise ValueError('Persona no encontrada')
                    except IndexError:
                        raise ValueError('El nombre o apellido no tiene el formato correcto')
                    except Exception as e:
                        raise ValueError(str(e))

                # Procesar primer líder
                if persona_lider1_id:
                    try:
                        lider1 = crear_usuario_lider(persona_lider1_id)
                        usuarios_creados['lider1'] = {
                            'id_usuario': lider1.id_usuario,
                            'usuario': lider1.usuario,
                            'id_persona': lider1.id_persona.id_persona
                        }
                    except ValueError as e:
                        return JsonResponse({'error': f'Líder 1 no válido: {str(e)}'}, status=400)

                # Procesar segundo líder
                if persona_lider2_id:
                    try:
                        if persona_lider1_id and int(persona_lider2_id) == int(persona_lider1_id):
                            return JsonResponse({'error': 'Una persona no puede ser ambos líderes'}, status=400)
                        
                        lider2 = crear_usuario_lider(persona_lider2_id)
                        usuarios_creados['lider2'] = {
                            'id_usuario': lider2.id_usuario,
                            'usuario': lider2.usuario,
                            'id_persona': lider2.id_persona.id_persona
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
                    response_data['detalle_credenciales'] = {
                        'formato_usuario': 'primer_nombre.primer_apellido',
                        'formato_password': 'número_de_cédula'
                    }

                return JsonResponse(response_data, status=201)

        except Exception as e:
            error_trace = traceback.format_exc()  # Captura el traceback completo
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
                def procesar_lider(persona_id, lider_actual):
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
                        
                        # Buscar o crear usuario líder
                        rol_lider = Rol.objects.get(id_rol=2)
                        primer_nombre = persona.nombres.split()[0].lower()
                        primer_apellido = persona.apellidos.split()[0].lower()
                        username = f"{primer_nombre}.{primer_apellido}"
                        password = make_password(persona.numero_cedula)
                        
                        usuario, created = Usuario.objects.get_or_create(
                            id_persona=persona,
                            defaults={
                                'id_rol': rol_lider,
                                'usuario': username,
                                'contrasenia': password,
                                'activo': True
                            }
                        )
                        
                        if not created:
                            usuario.id_rol = rol_lider
                            usuario.activo = True
                            usuario.save()
                            
                        return usuario
                    
                    except Exception as e:
                        raise ValueError(str(e))

                # 6. Procesar nuevos líderes
                nuevos_lideres = {}
                errores = {}
                
                if nuevo_lider1_id is not None:  # None significa que no se envió, '' significa que se quiere quitar
                    try:
                        nuevos_lideres['lider1'] = procesar_lider(nuevo_lider1_id, lideres_originales['lider1']) if nuevo_lider1_id != '' else None
                    except ValueError as e:
                        errores['lider1'] = str(e)

                if nuevo_lider2_id is not None:
                    try:
                        nuevos_lideres['lider2'] = procesar_lider(nuevo_lider2_id, lideres_originales['lider2']) if nuevo_lider2_id != '' else None
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