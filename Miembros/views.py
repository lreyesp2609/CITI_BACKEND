from django.shortcuts import render
import jwt
from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from Login.models import Persona, Rol

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
            personas = Persona.objects.all()
            
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
                    'correo_electronico': persona.correo_electronico
                })
            
            return JsonResponse({'personas': personas_list}, status=200)
            
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
                    'correo_electronico': persona.correo_electronico
                }
                
                return JsonResponse({'persona': persona_data}, status=200)
                
            except Persona.DoesNotExist:
                return JsonResponse({'error': 'Persona no encontrada'}, status=404)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)