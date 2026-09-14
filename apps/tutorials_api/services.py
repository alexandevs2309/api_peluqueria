import os
import re
import logging
from typing import Optional, Dict, Any
import requests
from django.conf import settings
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class YouTubeService:
    """Servicio para interactuar con YouTube Data API v3"""
    
    API_BASE_URL = "https://www.googleapis.com/youtube/v3"
    
    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """
        Extrae el video ID de una URL de YouTube.
        
        Soporta:
        - youtube.com/watch?v=VIDEO_ID
        - youtu.be/VIDEO_ID
        - youtube.com/embed/VIDEO_ID
        - youtube.com/shorts/VIDEO_ID
        - youtube.com/v/VIDEO_ID
        """
        if not url:
            return None
            
        try:
            parsed = urlparse(url)
            
            # youtube.com/watch?v=VIDEO_ID
            if parsed.hostname in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
                if parsed.path == '/watch':
                    query_params = parse_qs(parsed.query)
                    video_id = query_params.get('v', [None])[0]
                    return video_id
                # youtube.com/embed/VIDEO_ID
                elif parsed.path.startswith('/embed/'):
                    return parsed.path.split('/')[2]
                # youtube.com/shorts/VIDEO_ID
                elif parsed.path.startswith('/shorts/'):
                    return parsed.path.split('/')[2]
                # youtube.com/v/VIDEO_ID
                elif parsed.path.startswith('/v/'):
                    return parsed.path.split('/')[2]
            
            # youtu.be/VIDEO_ID
            elif parsed.hostname == 'youtu.be':
                return parsed.path.lstrip('/').split('?')[0]
            
        except Exception as e:
            logger.error(f"Error extrayendo video ID de URL: {url}. Error: {e}")
            
        return None
    
    @staticmethod
    def is_valid_youtube_url(url: str) -> bool:
        """Verifica si una URL es válida de YouTube"""
        video_id = YouTubeService.extract_video_id(url)
        return video_id is not None
    
    @staticmethod
    def normalize_embed_url(video_id: str) -> str:
        """Normaliza el video ID a URL de embed"""
        return f"https://www.youtube.com/embed/{video_id}"
    
    @staticmethod
    def get_thumbnail_url(video_id: str, quality: str = 'maxres') -> str:
        """Genera URL de thumbnail para un video ID"""
        qualities = ['maxres', 'standard', 'high', 'medium', 'default']
        
        if quality not in qualities:
            quality = qualities[0]
            
        return f"https://i.ytimg.com/vi/{video_id}/{quality}default.jpg"
    
    @classmethod
    def get_video_metadata(cls, url_or_id: str) -> Dict[str, Any]:
        """
        Obtiene metadatos de un video de YouTube usando la API.
        
        Args:
            url_or_id: URL de YouTube o video ID
            
        Returns:
            Dict con metadatos del video o error
        """
        # Extraer video ID si es una URL
        is_url = 'youtube' in url_or_id.lower() or 'youtu.be' in url_or_id.lower()
        video_id = cls.extract_video_id(url_or_id) if is_url else url_or_id
        
        if not video_id:
            logger.warning(f"Video ID no encontrado en: {url_or_id[:50]}...")
            return {
                'error': 'ID de video inválido - no se pudo extraer de la URL',
                'error_code': 'INVALID_VIDEO_ID',
                'video_id': None
            }
        
        if len(video_id) != 11:
            logger.warning(f"Video ID con longitud incorrecta: {video_id} (len={len(video_id)})")
            return {
                'error': 'ID de video inválido - longitud incorrecta',
                'error_code': 'INVALID_VIDEO_ID_LENGTH',
                'video_id': video_id
            }
        
        # Validar formato del video ID
        import re
        video_id_pattern = r'^[a-zA-Z0-9_-]{11}$'
        if not re.match(video_id_pattern, video_id):
            logger.warning(f"Video ID con formato inválido: {video_id}")
            return {
                'error': 'ID de video inválido - formato incorrecto',
                'error_code': 'INVALID_VIDEO_ID_FORMAT',
                'video_id': video_id
            }
        
        api_key = getattr(settings, 'YOUTUBE_API_KEY', None) or os.environ.get('YOUTUBE_API_KEY')
        if not api_key:
            logger.warning("YOUTUBE_API_KEY no configurada en variables de entorno")
            return {
                'error': 'Configuración de YouTube API incompleta',
                'error_code': 'API_KEY_MISSING',
                'video_id': video_id
            }
        
        # Verificar si la API key es válida (no placeholder)
        if api_key.startswith('AIza') and len(api_key) < 20:
            logger.warning("YOUTUBE_API_KEY parece ser un placeholder")
            return {
                'error': 'Configuración de YouTube API inválida',
                'error_code': 'API_KEY_INVALID',
                'video_id': video_id
            }
        
        try:
            # Llamar a YouTube Data API
            logger.info(f"Consultando YouTube API para video ID: {video_id}")
            response = requests.get(
                f"{cls.API_BASE_URL}/videos",
                params={
                    'part': 'snippet,contentDetails',
                    'id': video_id,
                    'key': api_key
                },
                timeout=15  # Timeout aumentado a 15 segundos
            )
            
            # Verificar límites de cuota
            if response.status_code == 403:
                logger.error(f"Error 403 en YouTube API: {response.text[:200]}")
                return {
                    'error': 'Límite de cuota de YouTube API excedido',
                    'error_code': 'API_QUOTA_EXCEEDED',
                    'video_id': video_id
                }
            
            response.raise_for_status()
            data = response.json()
            
            if not data.get('items'):
                logger.warning(f"Video no encontrado en YouTube API: {video_id}")
                return {
                    'error': 'Video no encontrado, eliminado o privado',
                    'error_code': 'VIDEO_NOT_FOUND',
                    'video_id': video_id
                }
            
            video_data = data['items'][0]
            snippet = video_data.get('snippet', {})
            content_details = video_data.get('contentDetails', {})
            
            # Verificar si el video está restringido
            if snippet.get('liveBroadcastContent') == 'live':
                logger.info(f"Video {video_id} es un stream en vivo")
            
            # Obtener mejor thumbnail disponible
            thumbnails = snippet.get('thumbnails', {})
            thumbnail_url = None
            
            for quality in ['maxres', 'standard', 'high', 'medium', 'default']:
                if quality in thumbnails:
                    thumbnail_url = thumbnails[quality]['url']
                    break
            
            # Convertir duración ISO 8601 a segundos y luego a formato HH:MM:SS
            duration_iso = content_details.get('duration', 'PT0S')
            duration_seconds = cls._iso_duration_to_seconds(duration_iso)
            duration_formatted = cls._seconds_to_hhmmss(duration_seconds)
            
            logger.info(f"Metadatos obtenidos exitosamente para video: {video_id}")
            
            return {
                'video_id': video_id,
                'title': snippet.get('title', ''),
                'description': snippet.get('description', ''),
                'thumbnail_url': thumbnail_url or cls.get_thumbnail_url(video_id),
                'duration_iso': duration_iso,
                'duration_seconds': duration_seconds,
                'duration': duration_formatted,
                'embed_url': cls.normalize_embed_url(video_id),
                'published_at': snippet.get('publishedAt', ''),
                'channel_title': snippet.get('channelTitle', ''),
                'is_live': snippet.get('liveBroadcastContent') == 'live'
            }
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout consultando YouTube API para video: {video_id}")
            return {
                'error': 'Timeout al consultar YouTube API',
                'error_code': 'API_TIMEOUT',
                'video_id': video_id
            }
        except requests.exceptions.ConnectionError:
            logger.error(f"Error de conexión con YouTube API para video: {video_id}")
            return {
                'error': 'Error de conexión con YouTube API',
                'error_code': 'API_CONNECTION_ERROR',
                'video_id': video_id
            }
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error HTTP {e.response.status_code} en YouTube API: {str(e)}")
            return {
                'error': f'Error HTTP {e.response.status_code} en YouTube API',
                'error_code': f'API_HTTP_{e.response.status_code}',
                'video_id': video_id
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de solicitud a YouTube API: {e}")
            return {
                'error': f'Error de conexión con YouTube API: {str(e)}',
                'error_code': 'API_REQUEST_ERROR',
                'video_id': video_id
            }
        except Exception as e:
            logger.error(f"Error inesperado obteniendo metadatos: {e}", exc_info=True)
            return {
                'error': f'Error inesperado: {str(e)}',
                'error_code': 'UNKNOWN_ERROR',
                'video_id': video_id
            }
    
    @staticmethod
    def _iso_duration_to_seconds(iso_duration: str) -> int:
        """Convierte duración ISO 8601 a segundos"""
        # Ejemplo: PT1H2M3S → 1 hora, 2 minutos, 3 segundos
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, iso_duration)
        
        if not match:
            return 0
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        return hours * 3600 + minutes * 60 + seconds
    
    @staticmethod
    def _seconds_to_hhmmss(seconds: int) -> str:
        """Convierte segundos a formato HH:MM:SS o MM:SS"""
        if seconds <= 0:
            return "0:00"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"