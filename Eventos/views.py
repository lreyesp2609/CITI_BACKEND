import jwt
from django.db import transaction
from django.views import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Evento, EstadoEvento, MotivosEvento
from Login.models import Usuario, Rol

@method_decorator(csrf_exempt, name='dispatch')
class CrearEventoView(View):
    def post(self, request, *args, **kwargs):
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)

            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                id_usuario = payload.get('id_usuario')
                rol_id = payload.get('rol')
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            required_fields = ['nombre', 'id_ministerio', 'descripcion', 'fecha', 'hora']
            for field in required_fields:
                if field not in request.POST:
                    return JsonResponse({'error': f'El campo {field} es obligatorio'}, status=400)

            with transaction.atomic():
                estado_inicial = 2 if rol_id == 1 else 1

                evento = Evento.objects.create(
                    nombre=request.POST['nombre'],
                    id_ministerio_id=request.POST['id_ministerio'],
                    descripcion=request.POST['descripcion'],
                    fecha=request.POST['fecha'],
                    hora=request.POST['hora'],
                    lugar=request.POST.get('lugar', ''),
                    id_usuario_id=id_usuario,
                    id_estado_id=estado_inicial
                )

                if rol_id == 1:
                    MotivosEvento.objects.create(
                        id_evento=evento,
                        id_usuario_id=id_usuario,
                        descripcion="Aprobado automáticamente por pastor"
                    )

                return JsonResponse({
                    'mensaje': 'Evento creado exitosamente',
                    'id_evento': evento.id_evento,
                    'estado': 'Aprobado' if rol_id == 1 else 'Pendiente'
                }, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class EditarEventoView(View):
    def post(self, request, id_evento, *args, **kwargs):
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)

            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                usuario_id = payload.get('id_usuario')
                rol_id = payload.get('rol')
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            if 'id_evento' not in request.POST:
                return JsonResponse({'error': 'ID de evento es obligatorio'}, status=400)

            with transaction.atomic():
                try:
                    evento = Evento.objects.get(id_evento=id_evento)
                except Evento.DoesNotExist:
                    return JsonResponse({'error': 'Evento no encontrado'}, status=404)

                if evento.id_usuario_id != usuario_id and rol_id != 1:
                    return JsonResponse({'error': 'No tiene permisos para editar este evento'}, status=403)

                for field in ['nombre', 'id_ministerio', 'descripcion', 'fecha', 'hora', 'lugar']:
                    if field in request.POST:
                        setattr(evento, field if field != 'id_ministerio' else 'id_ministerio_id', request.POST[field])

                evento.id_estado_id = 2 if rol_id == 1 else 1
                evento.save()

                if rol_id == 1:
                    MotivosEvento.objects.create(
                        id_evento=evento,
                        id_usuario_id=usuario_id,
                        descripcion="Aprobado automáticamente por edición de pastor"
                    )

                return JsonResponse({
                    'mensaje': 'Evento actualizado exitosamente',
                    'id_evento': evento.id_evento,
                    'estado': 'Aprobado' if rol_id == 1 else 'Pendiente'
                })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class CancelarEventoView(View):
    def post(self, request, id_evento, *args, **kwargs):
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)

            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                usuario_id = payload.get('id_usuario')
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            if 'id_evento' not in request.POST:
                return JsonResponse({'error': 'ID de evento es obligatorio'}, status=400)

            with transaction.atomic():
                try:
                    evento = Evento.objects.get(id_evento=id_evento)
                except Evento.DoesNotExist:
                    return JsonResponse({'error': 'Evento no encontrado'}, status=404)

                if evento.id_usuario_id != usuario_id:
                    return JsonResponse({'error': 'No tiene permisos para cancelar este evento'}, status=403)

                if evento.id_estado_id == 4:
                    nuevo_estado = 1
                    mensaje = 'Evento reactivado exitosamente'
                else:
                    nuevo_estado = 4
                    mensaje = 'Evento cancelado exitosamente'

                evento.id_estado_id = nuevo_estado
                evento.save()

                MotivosEvento.objects.create(
                    id_evento=evento,
                    id_usuario_id=usuario_id,
                    descripcion=request.POST.get('motivo', 'Cancelado/reactivado por usuario')
                )

                return JsonResponse({
                    'mensaje': mensaje,
                    'id_evento': evento.id_evento,
                    'estado': 'Cancelado' if nuevo_estado == 4 else 'Pendiente'
                })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class AprobarRechazarEventoView(View):
    def post(self, request, id_evento, *args, **kwargs):
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)

            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                usuario_id = payload.get('id_usuario')
                rol_id = payload.get('rol')
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            if rol_id not in [1, 2]:
                return JsonResponse({'error': 'No tiene permisos para aprobar/rechazar eventos'}, status=403)

            required_fields = ['id_evento', 'accion', 'motivo']
            for field in required_fields:
                if field not in request.POST:
                    return JsonResponse({'error': f'El campo {field} es obligatorio'}, status=400)

            if request.POST['accion'] not in ['aprobar', 'rechazar']:
                return JsonResponse({'error': 'Acción debe ser "aprobar" o "rechazar"'}, status=400)

            with transaction.atomic():
                try:
                    evento = Evento.objects.get(id_evento=id_evento)
                except Evento.DoesNotExist:
                    return JsonResponse({'error': 'Evento no encontrado'}, status=404)

                nuevo_estado = 2 if request.POST['accion'] == 'aprobar' else 3
                evento.id_estado_id = nuevo_estado
                evento.save()

                MotivosEvento.objects.create(
                    id_evento=evento,
                    id_usuario_id=usuario_id,
                    descripcion=request.POST['motivo']
                )

                return JsonResponse({
                    'mensaje': f"Evento {request.POST['accion']}ado exitosamente",
                    'id_evento': evento.id_evento,
                    'estado': 'Aprobado' if nuevo_estado == 2 else 'Rechazado'
                })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ListarEventosView(View):
    def get(self, request, *args, **kwargs):
        try:
            # Autenticación
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)
                
            token = auth_header.split('Bearer ')[1] if 'Bearer ' in auth_header else auth_header

            try:
                jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            eventos = Evento.objects.all().order_by('-fecha')

            eventos_data = [
                {
                    'id_evento': e.id_evento,
                    'nombre': e.nombre,
                    'descripcion': e.descripcion,
                    'fecha': e.fecha,
                    'hora': e.hora,
                    'lugar': e.lugar,
                    'estado': e.id_estado.nombre,
                    'ministerio': e.id_ministerio.nombre,
                    'usuario': f"{e.id_usuario.id_persona.nombres} {e.id_usuario.id_persona.apellidos}"
                }
                for e in eventos
            ]

            return JsonResponse({'eventos': eventos_data}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ObtenerEventoView(View):
    def get(self, request, id_evento, *args, **kwargs):
        try:
            # Autenticación
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)

            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header

            try:
                jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            try:
                evento = Evento.objects.get(id_evento=id_evento)
            except Evento.DoesNotExist:
                return JsonResponse({'error': 'Evento no encontrado'}, status=404)

            data = {
                'id_evento': evento.id_evento,
                'nombre': evento.nombre,
                'descripcion': evento.descripcion,
                'fecha': evento.fecha,
                'hora': evento.hora,
                'lugar': evento.lugar,
                'estado': evento.id_estado.nombre,
                'ministerio': evento.id_ministerio.nombre,
                'usuario': f"{evento.id_usuario.id_persona.nombres} {evento.id_usuario.id_persona.apellidos}"
            }

            return JsonResponse({'evento': data}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)