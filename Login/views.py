import jwt
from django.db import transaction
from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth import logout
from .models import Usuario, Rol, Persona

@method_decorator(csrf_exempt, name='dispatch')
class IniciarSesionView(View):
    def generate_token(self, usuario):
        payload = {
            'id_usuario': usuario.id_usuario,
            'nombre_usuario': usuario.usuario,
            'rol': usuario.id_rol.rol,
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        return token

    def post(self, request, *args, **kwargs):
        try:
            nombre_usuario = request.POST.get('usuario')
            contrasenia = request.POST.get('contrasenia')

            user = Usuario.objects.select_related('id_rol').filter(usuario=nombre_usuario).first()

            if user:
                if check_password(contrasenia, user.contrasenia):
                    token = self.generate_token(user)

                    return JsonResponse({
                        'token': token,
                        'nombre_usuario': nombre_usuario,
                        'id_usuario': user.id_usuario,
                        'rol': user.id_rol.id_rol,
                    })
                else:
                    return JsonResponse({'mensaje': 'Contraseña incorrecta'}, status=401)
            else:
                return JsonResponse({'mensaje': 'Credenciales incorrectas'}, status=401)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
@method_decorator(csrf_exempt, name='dispatch')
class CerrarSesionView(View):
    def post(self, request, *args, **kwargs):
        try:
            # Obtener el token del encabezado Authorization
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)
                
            # Extraer el token si viene con el prefijo Bearer
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            else:
                token = auth_header
                
            # No necesitamos validar el token aquí, solo reconocer el cierre de sesión
            # La función logout() de Django es principalmente para autenticación basada en sesiones, no en tokens
            
            # Django no maneja tokens JWT, así que no hay nada que invalidar en el servidor
            # El frontend debe eliminar el token del almacenamiento local
            
            logout(request)  # Esto limpia la sesión actual, aunque no afecta a los tokens JWT
            
            return JsonResponse({'mensaje': 'Sesión cerrada exitosamente'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

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
class ValidarTokenView(View):
    def get(self, request):
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'valid': False}, status=401)
                
            token = auth_header.split(' ')[1] if 'Bearer ' in auth_header else auth_header
            jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            return JsonResponse({'valid': True})
            
        except jwt.ExpiredSignatureError:
            return JsonResponse({'valid': False}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({'valid': False}, status=401)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)