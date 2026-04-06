"""
Serializers for Smart Audio Blog Experience API
"""
from rest_framework import serializers
from django.conf import settings

from .models import AudioFile, UserAudioPreference


class AudioGenerationSerializer(serializers.Serializer):
    """Serializer for audio generation request."""
    mode = serializers.ChoiceField(
        choices=['conversation', 'explain', 'summary'],
        default='explain',
        help_text="Audio transformation mode"
    )
    language = serializers.ChoiceField(
        choices=['en', 'hi', 'gu'],
        default='en',
        help_text="Audio language"
    )
    understanding_level = serializers.ChoiceField(
        choices=['beginner', 'intermediate', 'expert'],
        default='intermediate',
        help_text="Content complexity level"
    )
    mood = serializers.ChoiceField(
        choices=['serious', 'storytelling', 'educational'],
        default='educational',
        help_text="Voice style"
    )


class AudioFileSerializer(serializers.ModelSerializer):
    """Serializer for AudioFile model."""
    audio_url = serializers.SerializerMethodField()
    is_ready = serializers.SerializerMethodField()

    class Meta:
        model = AudioFile
        fields = [
            'id',
            'mode',
            'language',
            'understanding_level',
            'mood',
            'status',
            'audio_url',
            'duration_seconds',
            'sections',
            'transcript',
            'summary',
            'suggestions',
            'questions',
            'error_message',
            'is_ready',
            'created_at',
            'download_count',
        ]
        read_only_fields = [
            'status',
            'duration_seconds',
            'sections',
            'transcript',
            'summary',
            'suggestions',
            'questions',
            'error_message',
            'created_at',
            'download_count',
        ]

    def get_audio_url(self, obj):
        """Return the URL to the audio file."""
        request = self.context.get('request')
        if obj.audio_file and hasattr(obj.audio_file, 'url'):
            if request:
                return request.build_absolute_uri(obj.audio_file.url)
            return obj.audio_file.url
        return None

    def get_is_ready(self, obj):
        """Check if audio is ready for playback."""
        return obj.is_ready


class AudioFileListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing audio files."""
    audio_url = serializers.SerializerMethodField()

    class Meta:
        model = AudioFile
        fields = [
            'id',
            'mode',
            'language',
            'understanding_level',
            'mood',
            'status',
            'audio_url',
            'duration_seconds',
            'created_at',
        ]

    def get_audio_url(self, obj):
        """Return the URL to the audio file."""
        request = self.context.get('request')
        if obj.audio_file and hasattr(obj.audio_file, 'url'):
            if request:
                return request.build_absolute_uri(obj.audio_file.url)
            return obj.audio_file.url
        return None


class UserAudioPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for UserAudioPreference model."""

    class Meta:
        model = UserAudioPreference
        fields = [
            'default_mode',
            'default_language',
            'default_understanding_level',
            'default_mood',
            'default_speed',
            'default_volume',
            'autoplay',
            'highlight_sync_enabled',
        ]


class GenerateQuestionsSerializer(serializers.Serializer):
    """Serializer for generating comprehension questions."""
    num_questions = serializers.IntegerField(
        min_value=1,
        max_value=10,
        default=3,
        help_text="Number of questions to generate"
    )


class ReexplainSerializer(serializers.Serializer):
    """Serializer for re-explaining a section."""
    section = serializers.ChoiceField(
        choices=['intro', 'main', 'conclusion'],
        help_text="Section to re-explain"
    )


class QuestionAnswerSerializer(serializers.Serializer):
    """Serializer for answering a question."""
    question_id = serializers.IntegerField()
    answer = serializers.CharField()


class AudioStatusSerializer(serializers.Serializer):
    """Serializer for checking audio generation status."""
    status = serializers.CharField()
    progress = serializers.IntegerField(min_value=0, max_value=100, required=False)
    message = serializers.CharField(required=False)
    audio_url = serializers.URLField(required=False)
    duration_seconds = serializers.IntegerField(required=False)


class AudioSuggestionSerializer(serializers.Serializer):
    """Serializer for audio mode suggestions."""
    recommended_mode = serializers.CharField()
    recommended_level = serializers.CharField()
    reason = serializers.CharField()


class AudioGenerationResponseSerializer(serializers.Serializer):
    """Serializer for audio generation response."""
    audio_id = serializers.IntegerField()
    status = serializers.CharField()
    message = serializers.CharField()
    estimated_wait_seconds = serializers.IntegerField(required=False)