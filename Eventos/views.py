import json
import jwt
from django.db import transaction
from django.views import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from Login.models import *
from Ministerio.models import Ministerio
from .models import Evento, MotivosEvento, Notificaciones, TipoEvento

@method_decorator(csrf_exempt, name='dispatch')
class CrearEventoView(View):
    ESTADO_PENDIENTE = 1
    ESTADO_APROBADO = 2
    
    def post(self, request, *args, **kwargs):
        try:
            # Verificación del token (se mantiene igual)
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)

            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                id_usuario = payload.get('id_usuario')
                rol = payload.get('rol')
                
                if rol == "Pastor":
                    rol_id = 1
                else:
                    rol_id = 2
                    
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            # Campos obligatorios (añadimos id_tipo_evento como opcional)
            required_fields = ['nombre', 'id_ministerio', 'descripcion', 'fecha', 'hora']
            for field in required_fields:
                if field not in request.POST:
                    return JsonResponse({'error': f'El campo {field} es obligatorio'}, status=400)

            with transaction.atomic():
                estado_inicial = self.ESTADO_APROBADO if rol_id == 1 else self.ESTADO_PENDIENTE

                # Creación del evento con tipo de evento (si se proporciona)
                evento_data = {
                    'nombre': request.POST['nombre'],
                    'id_ministerio_id': request.POST['id_ministerio'],
                    'descripcion': request.POST['descripcion'],
                    'fecha': request.POST['fecha'],
                    'hora': request.POST['hora'],
                    'lugar': request.POST.get('lugar', ''),
                    'id_usuario_id': id_usuario,
                    'id_estado_id': estado_inicial,
                }

                # Añadir tipo de evento si está presente
                if 'id_tipo_evento' in request.POST and request.POST['id_tipo_evento']:
                    evento_data['id_tipo_evento_id'] = request.POST['id_tipo_evento']

                evento = Evento.objects.create(**evento_data)

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
                    'estado': estado_texto,
                    'id_tipo_evento': evento.id_tipo_evento_id if evento.id_tipo_evento else None
                }, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        
@method_decorator(csrf_exempt, name='dispatch')
class EditarEventoView(View):
    def post(self, request, id_evento, *args, **kwargs):
        try:
            # Autenticación y validación de token
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

            with transaction.atomic():
                try:
                    evento = Evento.objects.get(id_evento=id_evento)
                except Evento.DoesNotExist:
                    return JsonResponse({'error': 'Evento no encontrado'}, status=404)

                # Verificar permisos (solo el creador o un pastor puede editar)
                if evento.id_usuario_id != usuario_id and rol_id != 1:
                    return JsonResponse({'error': 'No tiene permisos para editar este evento'}, status=403)

                # Campos editables
                campos_editables = {
                    'nombre': 'nombre',
                    'id_ministerio': 'id_ministerio_id',
                    'descripcion': 'descripcion',
                    'fecha': 'fecha',
                    'hora': 'hora',
                    'lugar': 'lugar',
                    'id_tipo_evento': 'id_tipo_evento_id'  # Nuevo campo editable
                }

                # Actualizar campos proporcionados
                for field, field_db in campos_editables.items():
                    if field in request.POST:
                        # Validar tipo de evento si se proporciona
                        if field == 'id_tipo_evento' and request.POST[field]:
                            if not TipoEvento.objects.filter(id_tipo_evento=request.POST[field]).exists():
                                return JsonResponse({'error': 'El tipo de evento especificado no existe'}, status=400)
                        
                        setattr(evento, field_db, request.POST[field] if request.POST[field] else None)

                # Cambiar estado según quién edita
                nuevo_estado = 2 if rol_id == 1 else 1  # 2: Aprobado, 1: Pendiente
                evento.id_estado_id = nuevo_estado
                
                evento.save()

                # Registrar motivo si lo edita un pastor
                if rol_id == 1:
                    MotivosEvento.objects.create(
                        id_evento=evento,
                        id_usuario_id=usuario_id,
                        descripcion="Aprobado automáticamente por edición de pastor"
                    )

                return JsonResponse({
                    'mensaje': 'Evento actualizado exitosamente',
                    'id_evento': evento.id_evento,
                    'estado': 'Aprobado' if rol_id == 1 else 'Pendiente',
                    'id_tipo_evento': evento.id_tipo_evento_id,
                    'tipo_evento': evento.id_tipo_evento.nombre if evento.id_tipo_evento else None
                }, status=200)

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

                if evento.id_usuario_id != usuario_id:
                    return JsonResponse(
                        {'error': 'Solo el creador del evento puede cancelarlo/reactivarlo'}, 
                        status=403
                    )

                # Nueva lógica de estados
                if evento.id_estado_id == 4:  # Si está cancelado
                    nuevo_estado = 2  # Cambiar a aprobado (asumiendo que 2 es aprobado)
                    mensaje = 'Evento reactivado y aprobado exitosamente'
                else:  # Para cualquier otro estado
                    nuevo_estado = 4  # Cambiar a cancelado
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
                    'estado': 'Aprobado' if nuevo_estado == 2 else 'Cancelado'
                })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

def obtener_usuario_id(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        raise Exception('Token no proporcionado')
    
    token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
    return payload.get('id_usuario')

@method_decorator(csrf_exempt, name='dispatch')
class AprobarRechazarEventoView(View):
    def post(self, request, id_evento, *args, **kwargs):
        try:
            # Verificación de token y autenticación
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'Token no proporcionado'}, status=400)

            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                usuario_id = payload.get('id_usuario')
                rol_nombre = payload.get('rol')
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)

            # Verificar si es Pastor
            if rol_nombre != 'Pastor':
                return JsonResponse({'error': 'No tiene permisos para esta acción'}, status=403)

            with transaction.atomic():
                try:
                    data = json.loads(request.body)
                    accion = data.get('accion', '').lower()
                    motivo = data.get('motivo', '')
                except json.JSONDecodeError:
                    return JsonResponse({'error': 'Formato JSON inválido'}, status=400)

                # Validar acciones permitidas
                valid_actions = ['aprobar', 'rechazar', 'cancelar', 'posponer']
                if accion not in valid_actions:
                    return JsonResponse({
                        'error': 'Acción inválida',
                        'detalle': f'Valores permitidos: {", ".join(valid_actions)}'
                    }, status=400)

                try:
                    evento = Evento.objects.get(id_evento=id_evento)
                except Evento.DoesNotExist:
                    return JsonResponse({'error': 'Evento no encontrado'}, status=404)

                # Verificar si es el creador del evento
                es_creador = evento.id_usuario_id == usuario_id

                # Lógica para cancelación por otro pastor
                if accion == 'cancelar' and not es_creador:
                    if evento.id_estado_id != 2:  # Solo si está aprobado
                        return JsonResponse({
                            'error': 'Acción no permitida',
                            'detalle': 'Solo se pueden cancelar eventos aprobados'
                        }, status=400)
                    
                    # Crear notificación de solicitud de cancelación
                    Notificaciones.objects.create(
                        id_evento=evento,
                        id_usuario_remitente_id=usuario_id,
                        id_usuario_destino=evento.id_usuario,
                        tipo='solicitud_cancelacion',
                        mensaje=f"Solicitud de cancelación del evento '{evento.nombre}'. Motivo: {motivo}"
                    )
                    
                    return JsonResponse({
                        'mensaje': 'Solicitud de cancelación enviada al creador del evento',
                        'requiere_aprobacion': True
                    })

                # Mapeo de estados y validaciones
                state_mapping = {
                    'aprobar': {
                        'allowed_states': [1, 6],  # Pendiente o Pospuesto
                        'new_state': 2,  # Aprobado
                        'error_msg': 'Solo se pueden aprobar eventos pendientes o pospuestos'
                    },
                    'rechazar': {
                        'allowed_states': [1, 6],  # Pendiente o Pospuesto
                        'new_state': 3,  # Rechazado
                        'error_msg': 'Solo se pueden rechazar eventos pendientes o pospuestos'
                    },
                    'cancelar': {
                        'allowed_states': [2],  # Aprobado
                        'new_state': 4,  # Cancelado
                        'error_msg': 'Solo se pueden cancelar eventos aprobados'
                    },
                    'posponer': {
                        'allowed_states': [1],  # Pendiente
                        'new_state': 6,  # Pospuesto
                        'error_msg': 'Solo se pueden posponer eventos pendientes'
                    }
                }

                action_config = state_mapping.get(accion)
                if evento.id_estado_id not in action_config['allowed_states']:
                    return JsonResponse({
                        'error': 'Acción no permitida',
                        'detalle': action_config['error_msg']
                    }, status=400)

                # Actualizar estado del evento
                evento.id_estado_id = action_config['new_state']
                evento.save()

                # Registrar motivo
                estado_nombre = {
                    2: 'Aprobado',
                    3: 'Rechazado',
                    4: 'Cancelado',
                    6: 'Pospuesto'
                }.get(action_config['new_state'], 'Desconocido')

                MotivosEvento.objects.create(
                    id_evento=evento,
                    id_usuario_id=usuario_id,
                    descripcion=motivo or f"Evento {estado_nombre.lower()}"
                )

                return JsonResponse({
                    'mensaje': f"Evento {estado_nombre.lower()} exitosamente",
                    'id_evento': evento.id_evento,
                    'estado': estado_nombre
                })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class NotificacionesView(View):
    def get(self, request, *args, **kwargs):
        try:
            usuario_id = obtener_usuario_id(request)
            leida = request.GET.get('leida', None)
            
            queryset = Notificaciones.objects.filter(
                id_usuario_destino_id=usuario_id
            ).select_related(
                'id_evento',
                'id_evento__id_ministerio',
                'id_usuario_remitente',
                'id_usuario_remitente__id_persona'  # Nuevo: para obtener datos de la persona
            )
            
            if leida is not None:
                queryset = queryset.filter(leida=not bool(leida.lower() == 'true'))
            
            queryset = queryset.order_by('-fecha_creacion')
            
            data = []
            for n in queryset:
                evento_data = {
                    'id_evento': n.id_evento_id,
                    'nombre': n.id_evento.nombre if n.id_evento else None,
                    'ministerio': n.id_evento.id_ministerio.nombre if n.id_evento and n.id_evento.id_ministerio else None
                }
                
                # Datos del remitente
                remitente_data = None
                if n.id_usuario_remitente and n.id_usuario_remitente.id_persona:
                    remitente_data = {
                        'nombres': n.id_usuario_remitente.id_persona.nombres,
                        'apellidos': n.id_usuario_remitente.id_persona.apellidos
                    }
                
                data.append({
                    'id_notificacion': n.id_notificacion,
                    'evento': evento_data,
                    'remitente': remitente_data,  # Nuevo campo
                    'tipo': n.tipo,
                    'mensaje': n.mensaje,
                    'leida': n.leida,
                    'accion_tomada': n.accion_tomada,
                    'fecha_creacion': n.fecha_creacion.strftime('%Y-%m-%d %H:%M') if n.fecha_creacion else None
                })
            
            return JsonResponse({'notificaciones': data})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        
@method_decorator(csrf_exempt, name='dispatch')
class MarcarNotificacionLeidaView(View):
    def post(self, request, *args, **kwargs):
        try:
            usuario_id = obtener_usuario_id(request)
            data = json.loads(request.body)
            
            notificacion = Notificaciones.objects.get(
                id_notificacion=data.get('id_notificacion'),
                id_usuario_destino_id=usuario_id
            )
            
            notificacion.leida = True
            notificacion.save()
            
            return JsonResponse({'mensaje': 'Notificación marcada como leída'})
            
        except Notificaciones.DoesNotExist:
            return JsonResponse({'error': 'Notificación no encontrada'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ResponderNotificacionView(View):
    def post(self, request, *args, **kwargs):
        try:
            usuario_id = obtener_usuario_id(request)
            data = json.loads(request.body)
            
            notificacion = Notificaciones.objects.get(
                id_notificacion=data.get('id_notificacion'),
                id_usuario_destino_id=usuario_id
            )
            
            aprobada = data.get('aprobada')
            motivo_rechazo = data.get('motivo_rechazo', '')
            
            if notificacion.tipo == 'solicitud_cancelacion' and notificacion.accion_tomada is None:
                # Obtener datos del usuario que está respondiendo
                usuario_actual = Usuario.objects.get(id_usuario=usuario_id)
                persona_actual = Persona.objects.get(id_persona=usuario_actual.id_persona_id)
                
                # Obtener datos del evento
                evento = Evento.objects.get(id_evento=notificacion.id_evento_id)
                ministerio = Ministerio.objects.get(id_ministerio=evento.id_ministerio_id)
                
                if aprobada:
                    # Lógica de aprobación
                    evento.id_estado_id = 4  # Cancelado
                    evento.save()
                    
                    MotivosEvento.objects.create(
                        id_evento=evento,
                        id_usuario_id=usuario_id,
                        descripcion=f"Cancelación aprobada. Motivo original: {notificacion.mensaje}"
                    )
                else:
                    # Lógica de rechazo con todos los detalles
                    mensaje_rechazo = (
                        f"Tu solicitud de cancelación del evento '{evento.nombre}' "
                        f"(Ministerio: {ministerio.nombre}) fue rechazada por "
                        f"{persona_actual.nombres} {persona_actual.apellidos}. "
                        f"Motivo: {motivo_rechazo}"
                    )
                    
                    Notificaciones.objects.create(
                        id_evento=notificacion.id_evento,
                        id_usuario_remitente_id=usuario_id,
                        id_usuario_destino=notificacion.id_usuario_remitente,
                        tipo='respuesta_rechazo',
                        mensaje=mensaje_rechazo,
                        motivo_rechazo=motivo_rechazo
                    )
                
                notificacion.accion_tomada = aprobada
                notificacion.leida = True
                notificacion.save()
                
                return JsonResponse({
                    'mensaje': 'Respuesta registrada exitosamente',
                    'evento_actualizado': aprobada
                })
            
            return JsonResponse({'error': 'Notificación ya procesada'}, status=400)
            
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

            # Filtrar eventos solo del usuario actual con select_related para optimizar
            eventos = Evento.objects.filter(id_usuario_id=usuario_id)\
                                  .select_related('id_estado', 'id_ministerio', 'id_usuario', 'id_usuario__id_persona', 'id_tipo_evento')\
                                  .order_by('id_evento')

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
                    'id_tipo_evento': e.id_tipo_evento.id_tipo_evento if e.id_tipo_evento else None,
                    'tipo_evento': e.id_tipo_evento.nombre if e.id_tipo_evento else None
                }
                for e in eventos
            ]

            return JsonResponse({
                'eventos': eventos_data, 
                'total': len(eventos_data),
                'mensaje': 'Mis eventos obtenidos correctamente'
            }, status=200)

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

            # Filtrar eventos que NO son del usuario actual con select_related
            eventos = Evento.objects.exclude(id_usuario_id=usuario_id)\
                                   .select_related('id_estado', 'id_ministerio', 'id_usuario', 'id_usuario__id_persona', 'id_tipo_evento')\
                                   .order_by('id_evento')

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
                    'es_mio': False,
                    'id_tipo_evento': e.id_tipo_evento.id_tipo_evento if e.id_tipo_evento else None,
                    'tipo_evento': e.id_tipo_evento.nombre if e.id_tipo_evento else None
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
        
@method_decorator(csrf_exempt, name='dispatch')
class CrearTipoEventoView(View):
    def post(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                # Validar permisos
                id_usuario = obtener_usuario_id(request)
                usuario = Usuario.objects.select_for_update().get(id_usuario=id_usuario)
                if usuario.id_rol.id_rol != 1:
                    return JsonResponse({'error': 'Solo los pastores pueden crear tipos de evento'}, status=403)

                # Obtener y validar datos
                data = json.loads(request.body) if request.body else request.POST
                if 'nombre' not in data:
                    return JsonResponse({'error': 'El campo nombre es obligatorio'}, status=400)

                # Validar que el nombre no exista (insensible a mayúsculas)
                nombre = data['nombre'].strip()
                if TipoEvento.objects.filter(nombre__iexact=nombre).exists():
                    return JsonResponse({
                        'error': 'Ya existe un tipo de evento con este nombre',
                        'suggestion': 'Por favor use un nombre diferente'
                    }, status=400)

                # Crear el tipo de evento
                tipo_evento = TipoEvento.objects.create(
                    nombre=nombre,
                    descripcion=data.get('descripcion', '')
                )

                return JsonResponse({
                    'success': True,
                    'mensaje': 'Tipo de evento creado exitosamente',
                    'data': {
                        'id_tipo_evento': tipo_evento.id_tipo_evento,
                        'nombre': tipo_evento.nombre,
                        'descripcion': tipo_evento.descripcion
                    }
                }, status=201)

        except Usuario.DoesNotExist:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': f'Error al crear el tipo de evento: {str(e)}'}, status=500)
        
@method_decorator(csrf_exempt, name='dispatch')
class EditarTipoEventoView(View):
    def put(self, request, id_tipo_evento, *args, **kwargs):
        try:
            with transaction.atomic():
                # Validar permisos
                id_usuario = obtener_usuario_id(request)
                usuario = Usuario.objects.select_for_update().get(id_usuario=id_usuario)
                if usuario.id_rol.id_rol != 1:
                    return JsonResponse({'error': 'No autorizado'}, status=403)

                # Obtener datos
                data = json.loads(request.body) if request.body else {}
                tipo_evento = TipoEvento.objects.get(id_tipo_evento=id_tipo_evento)

                # Validar si se envió al menos un campo para editar
                if not any(key in data for key in ['nombre', 'descripcion']):
                    return JsonResponse({
                        'error': 'Debe proporcionar al menos un campo para editar (nombre o descripcion)'
                    }, status=400)

                # Validar nombre único si se está modificando
                if 'nombre' in data:
                    nuevo_nombre = data['nombre'].strip()
                    if nuevo_nombre != tipo_evento.nombre:
                        if TipoEvento.objects.filter(nombre__iexact=nuevo_nombre).exists():
                            return JsonResponse({
                                'error': 'Ya existe otro tipo de evento con este nombre',
                                'suggestion': 'Por favor use un nombre diferente'
                            }, status=400)
                        tipo_evento.nombre = nuevo_nombre

                # Actualizar descripción si se proporciona
                if 'descripcion' in data:
                    tipo_evento.descripcion = data['descripcion']

                tipo_evento.save()

                return JsonResponse({
                    'success': True,
                    'mensaje': 'Tipo de evento actualizado exitosamente',
                    'data': {
                        'id_tipo_evento': tipo_evento.id_tipo_evento,
                        'nombre': tipo_evento.nombre,
                        'descripcion': tipo_evento.descripcion,
                        'activo': tipo_evento.activo
                    }
                }, status=200)

        except TipoEvento.DoesNotExist:
            return JsonResponse({'error': 'Tipo de evento no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        
@method_decorator(csrf_exempt, name='dispatch')
class CambiarEstadoTipoEventoView(View):
    def patch(self, request, id_tipo_evento, *args, **kwargs):
        try:
            with transaction.atomic():
                # Validar permisos (solo pastores)
                id_usuario = obtener_usuario_id(request)
                usuario = Usuario.objects.select_for_update().get(id_usuario=id_usuario)
                if usuario.id_rol.id_rol != 1:
                    return JsonResponse({'error': 'No autorizado'}, status=403)

                # Cambiar estado
                tipo_evento = TipoEvento.objects.get(id_tipo_evento=id_tipo_evento)
                tipo_evento.activo = not tipo_evento.activo  # Invertir estado actual
                tipo_evento.save()

                return JsonResponse({
                    'success': True,
                    'mensaje': f'Tipo de evento {"activado" if tipo_evento.activo else "desactivado"} exitosamente',
                    'data': {
                        'id_tipo_evento': tipo_evento.id_tipo_evento,
                        'nombre': tipo_evento.nombre,
                        'activo': tipo_evento.activo
                    }
                }, status=200)

        except TipoEvento.DoesNotExist:
            return JsonResponse({'error': 'Tipo de evento no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        
@method_decorator(csrf_exempt, name='dispatch')
class ListarTiposEventoView(View):
    def get(self, request, *args, **kwargs):
        try:
            # Obtener usuario (validación opcional)
            id_usuario = obtener_usuario_id(request)
            usuario = Usuario.objects.get(id_usuario=id_usuario)
            
            # Consulta base - lista todos (activos e inactivos) ordenados por ID ascendente
            tipos_evento = TipoEvento.objects.all().order_by('id_tipo_evento')
            
            # Preparar respuesta simplificada
            data = [{
                'id_tipo_evento': tipo.id_tipo_evento,
                'nombre': tipo.nombre,
                'descripcion': tipo.descripcion,
                'activo': tipo.activo
            } for tipo in tipos_evento]
            
            return JsonResponse({
                'success': True,
                'count': len(data),
                'data': data
            }, status=200)

        except Usuario.DoesNotExist:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)