from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.shortcuts import render
import jwt
import json
from datetime import datetime
from Devocionales.models import Devocionales
from django.utils import timezone

def verificar_rol_admin(usuario_id):
    # Asume que tu modelo Usuarios tiene relación con Rol
    from Login.models import Usuario
    usuario = Usuario.objects.get(id_usuario=usuario_id)
    return usuario.id_rol.id_rol == 1  # Verifica si es rol 1 (admin)

def obtener_usuario_id(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        raise Exception('Token no proporcionado')
    
    token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
    return payload.get('id_usuario')

@method_decorator(csrf_exempt, name='dispatch')
class DevocionalesView(View):
    def post(self, request, *args, **kwargs):
        try:
            usuario_id = obtener_usuario_id(request)
            
            if not verificar_rol_admin(usuario_id):
                return JsonResponse({'error': 'No autorizado'}, status=403)
            
            data = json.loads(request.body)
            
            # Crear o actualizar devocional mensual
            devocional, created = Devocionales.objects.update_or_create(
                mes=data['mes'],
                año=data['año'],
                defaults={
                    'id_usuario_id': usuario_id,
                    'fecha': timezone.now().date(),
                    'titulo': data.get('titulo', ''),
                    'texto_biblico': data.get('texto_biblico', ''),
                    'reflexion': data.get('reflexion', ''),
                    'contenido_calendario': data.get('contenido_calendario', {}),  # Corregido aquí
                    'fecha_actualizacion': timezone.now()
                }
            )
            
            return JsonResponse({
                'status': 'success',
                'created': created,
                'id_devocional': devocional.id_devocional
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime
import json
from .models import Devocionales

@method_decorator(csrf_exempt, name='dispatch')
class HistorialDevocionalesView(View):
    def get(self, request):
        try:
            # Verificar token de autenticación
            usuario_id = obtener_usuario_id(request)
            if not usuario_id:
                return JsonResponse({'error': 'No autorizado'}, status=401)
            
            # Obtener parámetros de la solicitud
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            mes = request.GET.get('mes')
            año = request.GET.get('año')
            fecha_inicio = request.GET.get('fecha_inicio')
            fecha_fin = request.GET.get('fecha_fin')

            # Construir el queryset base
            devocionales = Devocionales.objects.all().order_by('-fecha_creacion')

            # Aplicar filtros
            if mes:
                devocionales = devocionales.filter(mes__iexact=mes.lower())
            if año:
                devocionales = devocionales.filter(año=int(año))
            if fecha_inicio and fecha_fin:
                fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                devocionales = devocionales.filter(
                    fecha_creacion__date__range=(fecha_inicio, fecha_fin))
            
            # Paginación manual
            total = devocionales.count()
            start = (page - 1) * page_size
            end = start + page_size
            devocionales_page = devocionales[start:end]

            # Preparar los datos para la respuesta
            resultados = []
            for devocional in devocionales_page:
                resultados.append({
                    'id_devocional': devocional.id_devocional,
                    'mes': devocional.mes,
                    'año': devocional.año,
                    'titulo': devocional.titulo,
                    'texto_biblico': devocional.texto_biblico,
                    'reflexion': devocional.reflexion,
                    'contenido_calendario': devocional.contenido_calendario,
                    'fecha_creacion': devocional.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S'),
                    'fecha_actualizacion': devocional.fecha_actualizacion.strftime('%Y-%m-%d %H:%M:%S'),
                    'usuario': {
                        'id': devocional.id_usuario.id_usuario,
                        'nombre': devocional.id_usuario.usuario
                    } if devocional.id_usuario else None
                })

            return JsonResponse({
                'count': total,
                'next': page * page_size < total,
                'previous': page > 1,
                'results': resultados
            })

        except ValueError as e:
            return JsonResponse({'error': 'Parámetros inválidos: ' + str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

from datetime import datetime
import calendar
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML, CSS
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import os

# Diccionario de meses en español
MESES_ESPANOL = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

@method_decorator(csrf_exempt, name='dispatch')
class GenerarPDFDevocional(View):
    def get(self, request, id_devocional):
        devocional = get_object_or_404(Devocionales, pk=id_devocional)
        
        # Diccionario inverso para obtener el número del mes
        meses_numero = {v.lower(): k for k, v in MESES_ESPANOL.items()}
        
        try:
            month_num = meses_numero[devocional.mes.lower()]
            year_num = devocional.año
            
            # Obtener calendario del mes
            cal = calendar.monthcalendar(year_num, month_num)
            semanas = []
            hoy = datetime.now().day
            
            # Procesar contenido del calendario
            contenido = {}
            for fecha_str, contenido_html in (devocional.contenido_calendario or {}).items():
                try:
                    # Convertir fecha de string a datetime
                    fecha = datetime.strptime(fecha_str[:10], "%Y-%m-%d")
                    if fecha.month == month_num and fecha.year == year_num:
                        # Almacenar por día del mes (1-31)
                        contenido[fecha.day] = contenido_html
                except (ValueError, TypeError):
                    continue
            
            # Generar estructura de semanas
            for week in cal:
                semana = []
                for day in week:
                    if day == 0:  # Días que no pertenecen al mes
                        dia_info = {
                            'numero': '',
                            'es_mes_actual': False,
                            'es_hoy': False,
                            'contenido': ''
                        }
                    else:
                        dia_info = {
                            'numero': day,
                            'es_mes_actual': True,
                            'es_hoy': (day == hoy and datetime.now().month == month_num),
                            'contenido': contenido.get(day, '')
                        }
                    semana.append(dia_info)
                semanas.append(semana)

            # Obtener ruta absoluta del logo
            logo_path = os.path.abspath(os.path.join(settings.BASE_DIR, 'static', 'img', 'Logo.webp'))
            
            # Renderizar PDF
            html_string = render_to_string('devocionales/pdf_template.html', {
            'devocional': devocional,
            'mes': MESES_ESPANOL.get(month_num, devocional.mes),
            'año': devocional.año,
            'semanas': semanas,
            'logo_path': 'file:///' + logo_path.replace('\\', '/')  # Ruta en formato file://
            })
            
            html = HTML(string=html_string)
            
            # CSS optimizado para una sola página
            css_string = '''
                @page {
                    size: A4 landscape;
                    margin: 0.5cm;
                }
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    padding: 10px;
                    margin: 0;
                    line-height: 1.4;
                    font-size: 12px;
                }
                .contenido-principal {
                    page-break-inside: avoid;
                    height: calc(100vh - 2cm);
                    display: flex;
                    flex-direction: column;
                }
            '''
            
            css = CSS(string=css_string)
            result = html.write_pdf(stylesheets=[css], presentational_hints=True)
            
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="devocional_{devocional.mes}_{devocional.año}.pdf"'
            response.write(result)
            return response
            
        except KeyError:
            return HttpResponse("Nombre de mes no válido", status=400)