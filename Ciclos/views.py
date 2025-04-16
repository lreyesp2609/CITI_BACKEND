from django.http import JsonResponse
from django.views import View
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import jwt
from .models import *
from django.conf import settings

@method_decorator(csrf_exempt, name='dispatch')
class CrearCicloView(View):
    def post(self, request, *args, **kwargs):
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)

            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                id_usuario = payload.get('id_usuario')
                rol = payload.get('rol')

                # Verificación adicional para el rol
                if rol != "Pastor":
                    return JsonResponse({'error': 'Acceso no autorizado, solo pastores pueden crear ciclos'}, status=403)

            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            required_fields = ['nombre', 'descripcion']
            for field in required_fields:
                if field not in request.POST:
                    return JsonResponse({'error': f'El campo {field} es obligatorio'}, status=400)

            with transaction.atomic():
                ciclo = Ciclo.objects.create(
                    nombre=request.POST['nombre'],
                    descripcion=request.POST['descripcion']
                )

                return JsonResponse({
                    'mensaje': 'Ciclo creado exitosamente',
                    'id_ciclo': ciclo.id_ciclo,
                    'nombre': ciclo.nombre
                }, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class EditarCicloView(View):
    def post(self, request, *args, **kwargs):
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)

            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                id_usuario = payload.get('id_usuario')
                rol = payload.get('rol')

                # Verificación adicional para el rol
                if rol != "Pastor":
                    return JsonResponse({'error': 'Acceso no autorizado, solo pastores pueden editar ciclos'}, status=403)

            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            ciclo_id = kwargs.get('id_ciclo')
            try:
                ciclo = Ciclo.objects.get(id_ciclo=ciclo_id)
            except Ciclo.DoesNotExist:
                return JsonResponse({'error': 'Ciclo no encontrado'}, status=404)

            required_fields = ['nombre', 'descripcion']
            for field in required_fields:
                if field not in request.POST:
                    return JsonResponse({'error': f'El campo {field} es obligatorio'}, status=400)

            with transaction.atomic():
                ciclo.nombre = request.POST['nombre']
                ciclo.descripcion = request.POST['descripcion']
                ciclo.save()

                return JsonResponse({
                    'mensaje': 'Ciclo actualizado exitosamente',
                    'nombre': ciclo.nombre,
                    'descripcion': ciclo.descripcion
                }, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        
@method_decorator(csrf_exempt, name='dispatch')
class ListarCiclosView(View):
    def get(self, request, *args, **kwargs):
        try:
            ciclos = Ciclo.objects.all()
            ciclo_data = [{
                'id_ciclo': ciclo.id_ciclo,
                'nombre': ciclo.nombre,
                'descripcion': ciclo.descripcion
            } for ciclo in ciclos]

            return JsonResponse({
                'ciclos': ciclo_data
            }, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class VerCicloView(View):
    def get(self, request, *args, **kwargs):
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)

            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                id_usuario = payload.get('id_usuario')
                rol = payload.get('rol')

            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            ciclo_id = kwargs.get('id_ciclo')
            try:
                ciclo = Ciclo.objects.get(id_ciclo=ciclo_id)
            except Ciclo.DoesNotExist:
                return JsonResponse({'error': 'Ciclo no encontrado'}, status=404)

            return JsonResponse({
                'id_ciclo': ciclo.id_ciclo,
                'nombre': ciclo.nombre,
                'descripcion': ciclo.descripcion
            }, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
