"""
API Views for Smart Audio Blog Experience

Provides endpoints for:
- Audio generation and retrieval
- Status checking
- Comprehension questions
- User preferences
"""
import logging
import mimetypes
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.shortcuts import get_object_or_404
from django.http import FileResponse

from blog_app.models import Blog

from .models import AudioFile, UserAudioPreference
from .serializers import (
    AudioGenerationSerializer,
    AudioFileSerializer,
    AudioFileListSerializer,
    UserAudioPreferenceSerializer,
    GenerateQuestionsSerializer,
    ReexplainSerializer,
    AudioStatusSerializer,
    AudioGenerationResponseSerializer,
)
from .tasks import (
    generate_blog_audio_task,
    generate_questions_for_audio_task,
    reexplain_audio_section_task,
)

logger = logging.getLogger(__name__)


class AudioViewSet(viewsets.ViewSet):
    """
    ViewSet for audio-related operations.

    Endpoints:
    - POST /api/blogs/{blog_id}/audio/generate/ - Generate audio
    - GET /api/blogs/{blog_id}/audio/status/ - Check generation status
    - GET /api/blogs/{blog_id}/audio/ - Get audio file
    - POST /api/blogs/{blog_id}/audio/questions/ - Generate questions
    - POST /api/blogs/{blog_id}/audio/reexplain/ - Re-explain section
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Generate audio for a blog in the specified mode and language",
        request_body=AudioGenerationSerializer,
        responses={
            201: AudioGenerationResponseSerializer,
            400: "Invalid parameters",
            403: "Blog not accessible",
            404: "Blog not found",
        },
        tags=['Audio']
    )
    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request, blog_pk=None):
        """
        Generate audio for a blog.

        Creates an AudioFile record and queues a Celery task for generation.
        Returns immediately with the audio ID and status.
        """
        blog = get_object_or_404(Blog, pk=blog_pk)

        # Check if blog is accessible
        if not blog.is_published and blog.author != request.user:
            return Response(
                {'detail': 'You do not have access to this blog.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate request data
        serializer = AudioGenerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mode = serializer.validated_data['mode']
        language = serializer.validated_data['language']
        understanding_level = serializer.validated_data['understanding_level']
        mood = serializer.validated_data['mood']

        # Check if any AudioFile exists with these parameters (unique constraint fields)
        existing_audio = AudioFile.objects.filter(
            blog=blog,
            mode=mode,
            language=language,
            understanding_level=understanding_level,
            mood=mood
        ).first()

        if existing_audio:
            # Handle existing record based on its status
            if existing_audio.status == 'ready':
                # Already available
                return Response({
                    'audio_id': existing_audio.id,
                    'status': 'ready',
                    'message': 'Audio already available',
                    'audio_url': self._get_audio_url(existing_audio, request),
                    'duration_seconds': existing_audio.duration_seconds,
                }, status=status.HTTP_200_OK)
            elif existing_audio.status in ['pending', 'processing']:
                # Generation already in progress
                return Response({
                    'audio_id': existing_audio.id,
                    'status': existing_audio.status,
                    'message': 'Audio generation in progress',
                    'estimated_wait_seconds': 30,
                }, status=status.HTTP_202_ACCEPTED)
            else:
                # For failed or any other status, reset and re-queue (regeneration)
                existing_audio.status = 'pending'
                existing_audio.error_message = ''
                existing_audio.audio_file = None
                existing_audio.duration_seconds = 0
                existing_audio.sections = {}
                existing_audio.transcript = ''
                existing_audio.summary = ''
                existing_audio.suggestions = []
                existing_audio.questions = []
                existing_audio.save()
                generate_blog_audio_task.delay(existing_audio.id)
                logger.info(f"Re-queued audio generation for existing audio {existing_audio.id}")
                return Response({
                    'audio_id': existing_audio.id,
                    'status': 'pending',
                    'message': 'Audio generation restarted',
                    'estimated_wait_seconds': 45,
                }, status=status.HTTP_202_ACCEPTED)

        # No existing record – create new AudioFile record
        audio_file = AudioFile.objects.create(
            blog=blog,
            mode=mode,
            language=language,
            understanding_level=understanding_level,
            mood=mood,
            status='pending'
        )

        # Queue the generation task
        generate_blog_audio_task.delay(audio_file.id)

        logger.info(f"Queued audio generation for blog {blog.id}, audio {audio_file.id}")

        return Response({
            'audio_id': audio_file.id,
            'status': 'pending',
            'message': 'Audio generation started',
            'estimated_wait_seconds': 45,
        }, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_description="Check audio generation status",
        manual_parameters=[
            openapi.Parameter(
                'mode',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Audio mode",
                enum=['conversation', 'explain', 'summary']
            ),
            openapi.Parameter(
                'language',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Audio language",
                enum=['en', 'hi', 'gu']
            ),
            openapi.Parameter(
                'understanding_level',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Understanding level",
                enum=['beginner', 'intermediate', 'expert']
            ),
            openapi.Parameter(
                'mood',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Voice mood",
                enum=['serious', 'storytelling', 'educational']
            ),
        ],
        responses={
            200: AudioStatusSerializer,
            404: "Audio not found",
        },
        tags=['Audio']
    )
    @action(detail=False, methods=['get'], url_path='status')
    def status_check(self, request, blog_pk=None):
        """Check the status of audio generation for a blog."""
        blog = get_object_or_404(Blog, pk=blog_pk)

        # Get parameters
        mode = request.query_params.get('mode', 'explain')
        language = request.query_params.get('language', 'en')
        understanding_level = request.query_params.get('understanding_level', 'intermediate')
        mood = request.query_params.get('mood', 'educational')

        # Find the audio file
        try:
            audio_file = AudioFile.objects.get(
                blog=blog,
                mode=mode,
                language=language,
                understanding_level=understanding_level,
                mood=mood,
            )
        except AudioFile.DoesNotExist:
            return Response({
                'status': 'not_found',
                'message': 'No audio found for this configuration. Generate audio first.',
            }, status=status.HTTP_404_NOT_FOUND)

        response_data = {
            'status': audio_file.status,
            'audio_id': audio_file.id,
        }

        if audio_file.status == 'ready':
            response_data['audio_url'] = self._get_audio_url(audio_file, request)
            response_data['duration_seconds'] = audio_file.duration_seconds
            response_data['sections'] = audio_file.sections

        elif audio_file.status == 'failed':
            response_data['message'] = audio_file.error_message

        elif audio_file.status in ['pending', 'processing']:
            response_data['message'] = 'Audio generation in progress'
            response_data['progress'] = 50 if audio_file.status == 'processing' else 10

        return Response(response_data)

    @swagger_auto_schema(
        operation_description="Get audio file and metadata",
        manual_parameters=[
            openapi.Parameter(
                'mode',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Audio mode",
                enum=['conversation', 'explain', 'summary']
            ),
            openapi.Parameter(
                'language',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Audio language",
                enum=['en', 'hi', 'gu']
            ),
            openapi.Parameter(
                'understanding_level',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Understanding level",
                enum=['beginner', 'intermediate', 'expert']
            ),
            openapi.Parameter(
                'mood',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Voice mood",
                enum=['serious', 'storytelling', 'educational']
            ),
        ],
        responses={
            200: AudioFileSerializer,
            404: "Audio not found",
        },
        tags=['Audio']
    )
    @action(detail=False, methods=['get'], url_path='')
    def get_audio(self, request, blog_pk=None):
        """Get audio file metadata and URL."""
        blog = get_object_or_404(Blog, pk=blog_pk)

        # Get parameters
        mode = request.query_params.get('mode', 'explain')
        language = request.query_params.get('language', 'en')
        understanding_level = request.query_params.get('understanding_level', 'intermediate')
        mood = request.query_params.get('mood', 'educational')

        # Find the audio file
        try:
            audio_file = AudioFile.objects.get(
                blog=blog,
                mode=mode,
                language=language,
                understanding_level=understanding_level,
                mood=mood,
                status='ready'
            )
        except AudioFile.DoesNotExist:
            return Response({
                'detail': 'Audio not found. Generate audio first.',
            }, status=status.HTTP_404_NOT_FOUND)

        # Increment download count
        audio_file.download_count += 1
        audio_file.save(update_fields=['download_count'])

        serializer = AudioFileSerializer(audio_file, context={'request': request})
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Download audio file",
        manual_parameters=[
            openapi.Parameter(
                'audio_id',
                openapi.IN_PATH,
                type=openapi.TYPE_INTEGER,
                description="Audio file ID"
            ),
        ],
        responses={
            200: "Audio file (MP3)",
            404: "Audio not found",
        },
        tags=['Audio']
    )
    @action(detail=False, methods=['get'], url_path=r'(?P<audio_id>\d+)/download')
    def download(self, request, blog_pk=None, audio_id=None):
        """Download the audio file directly."""
        blog = get_object_or_404(Blog, pk=blog_pk)

        audio_file = get_object_or_404(
            AudioFile,
            id=audio_id,
            blog=blog,
            status='ready'
        )

        if not audio_file.audio_file:
            return Response({
                'detail': 'Audio file not available.',
            }, status=status.HTTP_404_NOT_FOUND)

        # Increment download count
        audio_file.download_count += 1
        audio_file.save(update_fields=['download_count'])

        response = FileResponse(
            audio_file.audio_file.open('rb'),
            content_type=mimetypes.guess_type(audio_file.audio_file.name)[0] or 'application/octet-stream'
        )
        extension = audio_file.audio_file.name.rsplit('.', 1)[-1] if '.' in audio_file.audio_file.name else 'bin'
        response['Content-Disposition'] = f'attachment; filename="blog_{blog.id}_audio.{extension}"'
        return response

    @swagger_auto_schema(
        operation_description="Generate comprehension questions",
        request_body=GenerateQuestionsSerializer,
        responses={
            200: "Questions generated",
            404: "Audio not found",
        },
        tags=['Audio']
    )
    @action(detail=False, methods=['post'], url_path='questions')
    def generate_questions(self, request, blog_pk=None):
        """Generate comprehension questions for the audio."""
        blog = get_object_or_404(Blog, pk=blog_pk)

        serializer = GenerateQuestionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        num_questions = serializer.validated_data['num_questions']

        # Get parameters
        mode = request.data.get('mode', 'explain')
        language = request.data.get('language', 'en')
        understanding_level = request.data.get('understanding_level', 'intermediate')
        mood = request.data.get('mood', 'educational')

        # Find the audio file
        try:
            audio_file = AudioFile.objects.get(
                blog=blog,
                mode=mode,
                language=language,
                understanding_level=understanding_level,
                mood=mood,
                status='ready'
            )
        except AudioFile.DoesNotExist:
            return Response({
                'detail': 'Audio not found. Generate audio first.',
            }, status=status.HTTP_404_NOT_FOUND)

        # Queue question generation task
        generate_questions_for_audio_task.delay(audio_file.id, num_questions)

        return Response({
            'message': 'Question generation started',
            'audio_id': audio_file.id,
        })

    @swagger_auto_schema(
        operation_description="Re-explain a specific section",
        request_body=ReexplainSerializer,
        responses={
            200: "Re-explanation generated",
            404: "Audio not found",
        },
        tags=['Audio']
    )
    @action(detail=False, methods=['post'], url_path='reexplain')
    def reexplain(self, request, blog_pk=None):
        """Re-explain a specific section in more detail."""
        blog = get_object_or_404(Blog, pk=blog_pk)

        serializer = ReexplainSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        section = serializer.validated_data['section']

        # Get parameters
        mode = request.data.get('mode', 'explain')
        language = request.data.get('language', 'en')
        understanding_level = request.data.get('understanding_level', 'intermediate')
        mood = request.data.get('mood', 'educational')

        # Find the audio file
        try:
            audio_file = AudioFile.objects.get(
                blog=blog,
                mode=mode,
                language=language,
                understanding_level=understanding_level,
                mood=mood,
                status='ready'
            )
        except AudioFile.DoesNotExist:
            return Response({
                'detail': 'Audio not found. Generate audio first.',
            }, status=status.HTTP_404_NOT_FOUND)

        # Generate re-explanation
        result = reexplain_audio_section_task(audio_file.id, section)

        if result.get('status') == 'success':
            return Response({
                'section': section,
                'text': result.get('text'),
            })
        else:
            return Response({
                'detail': result.get('message', 'Failed to generate re-explanation'),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_description="List all audio files for a blog",
        responses={
            200: AudioFileListSerializer(many=True),
            404: "Blog not found",
        },
        tags=['Audio']
    )
    @action(detail=False, methods=['get'], url_path='list')
    def list_audio(self, request, blog_pk=None):
        """List all generated audio files for a blog."""
        blog = get_object_or_404(Blog, pk=blog_pk)

        audio_files = AudioFile.objects.filter(blog=blog, status='ready')
        serializer = AudioFileListSerializer(
            audio_files,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    def _get_audio_url(self, audio_file, request):
        """Helper to get full audio URL."""
        if audio_file.audio_file and hasattr(audio_file.audio_file, 'url'):
            if request:
                return request.build_absolute_uri(audio_file.audio_file.url)
            return audio_file.audio_file.url
        return None


class UserAudioPreferenceViewSet(viewsets.ViewSet):
    """
    ViewSet for user audio preferences.

    Endpoints:
    - GET /api/audio/preferences/ - Get user preferences
    - PUT /api/audio/preferences/ - Update user preferences
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get user audio preferences",
        responses={200: UserAudioPreferenceSerializer},
        tags=['Audio Preferences']
    )
    def list(self, request):
        """Get the current user's audio preferences."""
        preference, _ = UserAudioPreference.objects.get_or_create(
            user=request.user
        )
        serializer = UserAudioPreferenceSerializer(preference)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Update user audio preferences",
        request_body=UserAudioPreferenceSerializer,
        responses={200: UserAudioPreferenceSerializer},
        tags=['Audio Preferences']
    )
    def update(self, request):
        """Update user audio preferences."""
        preference, _ = UserAudioPreference.objects.get_or_create(
            user=request.user
        )
        serializer = UserAudioPreferenceSerializer(
            preference,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
