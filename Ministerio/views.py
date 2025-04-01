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
                                'contrasenia': password
                            }
                        )
                        
                        if not created:
                            # Si el usuario ya existe, actualizar a líder
                            usuario.id_rol = rol_lider
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
            return JsonResponse({'error': str(e)}, status=500)