from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from .models import Tutorial
from .serializers import TutorialSerializer
from apps.core.permissions import IsSuperAdmin
from .services import YouTubeService


class TutorialViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tutorial.objects.filter(is_published=True)
    serializer_class = TutorialSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        module = self.request.query_params.get('module')
        if module:
            qs = qs.filter(module=module)
        return qs


class AdminTutorialViewSet(viewsets.ModelViewSet):
    queryset = Tutorial.objects.all()
    serializer_class = TutorialSerializer
    permission_classes = [IsSuperAdmin]
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        module = self.request.query_params.get('module')
        if module:
            qs = qs.filter(module=module)
        return qs
    
    @action(detail=False, methods=['post'], url_path='youtube-metadata')
    def youtube_metadata(self, request: Request):
        """
        Endpoint para obtener metadatos de un video de YouTube.
        
        Recibe:
        {
            "url": "https://www.youtube.com/watch?v=VIDEO_ID"
        }
        
        o
        
        {
            "video_id": "VIDEO_ID"
        }
        """
        url = request.data.get('url')
        video_id = request.data.get('video_id')
        
        if not url and not video_id:
            return Response(
                {
                    'error': 'Se requiere URL o video_id',
                    'error_code': 'MISSING_INPUT'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar longitud máxima
        input_value = url if url else video_id
        if len(input_value) > 500:
            return Response(
                {
                    'error': 'URL o video ID demasiado largo',
                    'error_code': 'INPUT_TOO_LONG'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Si se proporciona URL, extraer video ID y validar
        if url:
            # Validar que sea una URL válida
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                if not parsed.scheme or not parsed.netloc:
                    return Response(
                        {
                            'error': 'URL inválida',
                            'error_code': 'INVALID_URL_FORMAT'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Exception:
                return Response(
                    {
                        'error': 'URL inválida',
                        'error_code': 'INVALID_URL_FORMAT'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar que sea URL de YouTube
            if not YouTubeService.is_valid_youtube_url(url):
                return Response(
                    {
                        'error': 'URL de YouTube inválida',
                        'error_code': 'INVALID_YOUTUBE_URL'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Obtener metadatos
        metadata = YouTubeService.get_video_metadata(input_value)
        
        if 'error' in metadata:
            error_code = metadata.get('error_code', 'UNKNOWN_ERROR')
            error_message = metadata['error']
            
            # Determinar código de estado HTTP apropiado
            if error_code in ['INVALID_VIDEO_ID', 'INVALID_VIDEO_ID_LENGTH', 'INVALID_VIDEO_ID_FORMAT', 
                            'INVALID_YOUTUBE_URL', 'INPUT_TOO_LONG']:
                status_code = status.HTTP_400_BAD_REQUEST  # Error del cliente
            elif error_code in ['API_KEY_MISSING', 'API_KEY_INVALID']:
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE  # Configuración del servidor
            elif error_code in ['VIDEO_NOT_FOUND']:
                status_code = status.HTTP_404_NOT_FOUND  # Recurso no encontrado
            elif error_code in ['API_QUOTA_EXCEEDED', 'API_TIMEOUT', 'API_CONNECTION_ERROR', 
                              'API_REQUEST_ERROR', 'API_HTTP_403', 'API_HTTP_429']:
                status_code = status.HTTP_502_BAD_GATEWAY  # Error del servicio externo
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR  # Error interno
            
            return Response(
                {
                    'error': error_message,
                    'error_code': error_code,
                    'video_id': metadata.get('video_id')
                },
                status=status_code
            )
        
        return Response(metadata, status=status.HTTP_200_OK)
