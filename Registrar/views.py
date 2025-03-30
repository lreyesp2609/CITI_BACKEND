from django.shortcuts import render
import jwt
from django.db import transaction
from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password
from Login.models import Usuario, Rol, Persona

@method_decorator(csrf_exempt, name='dispatch')
class CambiarContraseniaView(View):
    def post(self, request, id_usuario, *args, **kwargs):
        try:
            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)

            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            token_id_usuario = payload.get('id_usuario')

            if id_usuario != token_id_usuario:
                return JsonResponse({'error': 'No autorizado'}, status=401)

            nueva_contrasenia = request.POST.get('nueva_contrasenia')
            if not nueva_contrasenia:
                return JsonResponse({'error': 'La nueva contraseña es obligatoria'}, status=400)

            usuario = Usuario.objects.get(id_usuario=id_usuario)
            usuario.contrasenia = make_password(nueva_contrasenia)
            usuario.save()

            return JsonResponse({'mensaje': 'Contraseña cambiada exitosamente'}, status=200)

        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expirado'}, status=401)

        except jwt.InvalidTokenError:
            return JsonResponse({'error': 'Token inválido'}, status=401)

        except Usuario.DoesNotExist:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=404)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class RegistrarUsuarioView(View):
    def post(self, request, *args, **kwargs):
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
            
            # Decodificar el token directamente
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                rol_usuario = payload.get('rol')
                
                # Verificar si el rol está permitido (solo roles 1 y 2)
                rol_id = Rol.objects.filter(rol=rol_usuario).first()
                if not rol_id or rol_id.id_rol not in [1, 2]:
                    return JsonResponse({'error': 'No tiene permisos para registrar personas'}, status=403)
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)
            
            # Check required fields
            required_fields = ['nombres', 'apellidos']  # Removed 'numero_cedula'
            for field in required_fields:
                if not request.POST.get(field):
                    return JsonResponse({'error': f'El campo {field} es obligatorio'}, status=400)
            
            # Verificar si ya existe una persona con ese número de cédula (solo si se proporciona)
            numero_cedula = request.POST.get('numero_cedula', '')
            if numero_cedula and Persona.objects.filter(numero_cedula=numero_cedula).exists():
                return JsonResponse({'error': 'Ya existe una persona con este número de cédula'}, status=400)
            
            with transaction.atomic():
                nombres = request.POST.get('nombres')
                apellidos = request.POST.get('apellidos')
                correo_electronico = request.POST.get('correo_electronico', '')
                genero = request.POST.get('genero', '')  
                fecha_nacimiento = request.POST.get('fecha_nacimiento', None)
                
                # Nuevos campos
                nivel_estudio = request.POST.get('nivel_estudio', None)
                nacionalidad = request.POST.get('nacionalidad', None)
                profesion = request.POST.get('profesion', None)
                estado_civil = request.POST.get('estado_civil', None)
                lugar_trabajo = request.POST.get('lugar_trabajo', None)
                celular = request.POST.get('celular', None)
                direccion = request.POST.get('direccion', None)
                
                persona = Persona.objects.create(
                    nombres=nombres,
                    apellidos=apellidos,
                    numero_cedula=numero_cedula,
                    correo_electronico=correo_electronico,
                    genero=genero,
                    fecha_nacimiento=fecha_nacimiento,
                    # Nuevos campos
                    nivel_estudio=nivel_estudio,
                    nacionalidad=nacionalidad,
                    profesion=profesion,
                    estado_civil=estado_civil,
                    lugar_trabajo=lugar_trabajo,
                    celular=celular,
                    direccion=direccion
                )

                return JsonResponse({
                    'mensaje': 'Persona registrada exitosamente',
                    'id_persona': persona.id_persona
                }, status=201)

        except Exception as e:
            # Asegurarse de que cualquier error cause un rollback automático
            # debido al uso de transaction.atomic()
            return JsonResponse({'error': str(e)}, status=500)