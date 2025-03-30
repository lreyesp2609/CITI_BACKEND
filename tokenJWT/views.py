from django.http import JsonResponse
from django.views import View
import jwt
from django.conf import settings
from Login.models import Usuario, Persona, Rol
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class DecodificarTokenView(View):
    def post(self, request, *args, **kwargs):
        try:
            token = request.POST.get('token')

            if not token:
                return JsonResponse({'mensaje': 'Token no proporcionado'}, status=400)

            # Decodificar el token usando la misma clave secreta
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])

                # Obtener el id_usuario del payload
                id_usuario = payload.get('id_usuario')
                if not id_usuario:
                    return JsonResponse({'mensaje': 'El token no contiene id_usuario'}, status=400)

                # Obtener el usuario con sus relaciones
                usuario = Usuario.objects.select_related('id_persona', 'id_rol').filter(id_usuario=id_usuario).first()
                if not usuario:
                    return JsonResponse({'mensaje': 'Usuario no encontrado'}, status=404)

                # La persona está relacionada directamente con el usuario
                persona = usuario.id_persona
                if not persona:
                    return JsonResponse({'mensaje': 'Datos de persona no encontrados'}, status=404)

                # Responder con los datos de usuario y persona
                return JsonResponse({
                    'mensaje': 'Token decodificado correctamente',
                    'usuario': {
                        'id_usuario': usuario.id_usuario,
                        'usuario': usuario.usuario,
                        'rol': usuario.id_rol.rol,
                        'id_rol': usuario.id_rol.id_rol
                    },
                    'persona': {
                        'id_persona': persona.id_persona,
                        'numero_cedula': persona.numero_cedula,
                        'nombres': persona.nombres,
                        'apellidos': persona.apellidos,
                        'fecha_nacimiento': persona.fecha_nacimiento.strftime('%Y-%m-%d') if persona.fecha_nacimiento else None,
                        'genero': persona.genero,
                        'celular': persona.celular,
                        'direccion': persona.direccion,
                        'correo_electronico': persona.correo_electronico
                    }
                }, status=200)

            except jwt.ExpiredSignatureError:
                return JsonResponse({'mensaje': 'El token ha expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'mensaje': 'Token inválido'}, status=401)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)