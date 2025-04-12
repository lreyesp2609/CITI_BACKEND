import jwt
from django.db import transaction
from django.views import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Evento, MotivosEvento

@method_decorator(csrf_exempt, name='dispatch')
class CrearEventoView(View):
    ESTADO_PENDIENTE = 1
    ESTADO_APROBADO = 2
    
    def post(self, request, *args, **kwargs):
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)

            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                id_usuario = payload.get('id_usuario')
                rol = payload.get('rol')  # Cambiado de rol_id a rol
                
                # Verificación adicional para el rol
                if rol == "Pastor":
                    rol_id = 1
                else:
                    # Aquí puedes mapear otros roles si es necesario
                    rol_id = 2  # O cualquier otro valor por defecto
                    
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            required_fields = ['nombre', 'id_ministerio', 'descripcion', 'fecha', 'hora']
            for field in required_fields:
                if field not in request.POST:
                    return JsonResponse({'error': f'El campo {field} es obligatorio'}, status=400)

            with transaction.atomic():
                estado_inicial = self.ESTADO_APROBADO if rol_id == 1 else self.ESTADO_PENDIENTE

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

                estado_texto = "Aprobado" if rol_id == 1 else "Pendiente"
                return JsonResponse({
                    'mensaje': 'Evento creado exitosamente',
                    'id_evento': evento.id_evento,
                    'estado': estado_texto
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

            with transaction.atomic():
                try:
                    evento = Evento.objects.get(id_evento=id_evento)
                except Evento.DoesNotExist:
                    return JsonResponse({'error': 'Evento no encontrado'}, status=404)

                # Verificación de que el usuario es el creador del evento
                if evento.id_usuario_id != usuario_id:
                    return JsonResponse(
                        {'error': 'Solo el creador del evento puede cancelarlo/reactivarlo'}, 
                        status=403
                    )

                # Lógica para determinar nuevo estado
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
                    descripcion=request.POST.get('motivo', 'Cancelado/reactivado por el creador')
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

            # Cambiado: ordenar por id_evento ascendente (de menor a mayor)
            eventos = Evento.objects.all().order_by('id_evento')

            eventos_data = [
                {
                    'id_evento': e.id_evento,
                    'nombre': e.nombre,
                    'descripcion': e.descripcion,
                    'fecha': e.fecha,
                    'hora': e.hora,
                    'lugar': e.lugar,
                    'estado': e.id_estado.nombre,
                    'id_ministerio': e.id_ministerio.id_ministerio,
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
                'id_ministerio': evento.id_ministerio.id_ministerio,
                'ministerio': evento.id_ministerio.nombre,
                'usuario': f"{evento.id_usuario.id_persona.nombres} {evento.id_usuario.id_persona.apellidos}"
            }

            return JsonResponse({'evento': data}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        
@method_decorator(csrf_exempt, name='dispatch')
class ListarMisEventosView(View):
    def get(self, request, *args, **kwargs):
        try:
            # Autenticación
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)
                
            token = auth_header.split('Bearer ')[1] if 'Bearer ' in auth_header else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                usuario_id = payload.get('id_usuario')
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            # Filtrar eventos solo del usuario actual y ordenar por id_evento ascendente
            eventos = Evento.objects.filter(id_usuario_id=usuario_id).order_by('id_evento')

            eventos_data = [
                {
                    'id_evento': e.id_evento,
                    'nombre': e.nombre,
                    'descripcion': e.descripcion,
                    'fecha': e.fecha.strftime('%Y-%m-%d') if e.fecha else None,
                    'hora': e.hora.strftime('%H:%M:%S') if e.hora else None,
                    'lugar': e.lugar,
                    'estado': e.id_estado.nombre if e.id_estado else None,
                    'id_ministerio': e.id_ministerio.id_ministerio if e.id_ministerio else None,
                    'ministerio': e.id_ministerio.nombre if e.id_ministerio else None,
                    'usuario': f"{e.id_usuario.id_persona.nombres} {e.id_usuario.id_persona.apellidos}" if e.id_usuario and e.id_usuario.id_persona else None
                }
                for e in eventos
            ]

            return JsonResponse({'eventos': eventos_data, 'total': len(eventos_data)}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        
@method_decorator(csrf_exempt, name='dispatch')
class ListarEventosOtrosUsuariosView(View):
    def get(self, request, *args, **kwargs):
        try:
            # Autenticación
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)
                
            token = auth_header.split('Bearer ')[1] if 'Bearer ' in auth_header else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                usuario_id = payload.get('id_usuario')
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            # Filtrar eventos que NO son del usuario actual y ordenar por id_evento ascendente
            eventos = Evento.objects.exclude(id_usuario_id=usuario_id).order_by('id_evento')

            eventos_data = [
                {
                    'id_evento': e.id_evento,
                    'nombre': e.nombre,
                    'descripcion': e.descripcion,
                    'fecha': e.fecha.strftime('%Y-%m-%d') if e.fecha else None,
                    'hora': e.hora.strftime('%H:%M:%S') if e.hora else None,
                    'lugar': e.lugar,
                    'estado': e.id_estado.nombre if e.id_estado else None,
                    'id_ministerio': e.id_ministerio.id_ministerio if e.id_ministerio else None,
                    'ministerio': e.id_ministerio.nombre if e.id_ministerio else None,
                    'usuario': f"{e.id_usuario.id_persona.nombres} {e.id_usuario.id_persona.apellidos}" if e.id_usuario and e.id_usuario.id_persona else None,
                    'es_mio': False  # Agregamos este campo para identificar que no es del usuario
                }
                for e in eventos
            ]

            return JsonResponse({
                'eventos': eventos_data,
                'total': len(eventos_data),
                'mensaje': 'Eventos de otros usuarios obtenidos correctamente'
            }, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)