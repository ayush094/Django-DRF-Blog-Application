"""
Audio models for Smart Audio Blog Experience
"""
import os
import uuid
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils import timezone


def audio_file_path(instance, filename):
    """Generate unique file path for audio files"""
    ext = filename.split('.')[-1] if '.' in filename else 'mp3'
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('audio', str(instance.blog.id), filename)


class AudioFile(models.Model):
    """
    Generated audio files for blogs with multiple transformation modes.

    Supports:
    - Multiple modes: conversation, explain, summary
    - Multiple languages: en (English), hi (Hindi), gu (Gujarati)
    - Understanding levels: beginner, intermediate, expert
    - Mood styles: serious, storytelling, educational
    """

    MODE_CHOICES = [
        ('conversation', 'Conversation (Podcast Style)'),
        ('explain', 'Explain (Teacher Style)'),
        ('summary', 'Summary (Quick Overview)'),
    ]

    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('hi', 'Hindi (हिंदी)'),
        ('gu', 'Gujarati (ગુજરાતી)'),
    ]

    UNDERSTANDING_LEVEL_CHOICES = [
        ('beginner', 'Beginner - Simple explanations with analogies'),
        ('intermediate', 'Intermediate - Balanced depth and accessibility'),
        ('expert', 'Expert - Technical terms, focused insights'),
    ]

    MOOD_CHOICES = [
        ('serious', 'Serious - Professional tone'),
        ('storytelling', 'Storytelling - Narrative with dramatic elements'),
        ('educational', 'Educational - Clear, structured delivery'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending - Audio generation in queue'),
        ('processing', 'Processing - Audio being generated'),
        ('ready', 'Ready - Audio available for playback'),
        ('failed', 'Failed - Audio generation error'),
    ]

    # Relationships
    blog = models.ForeignKey(
        'blog_app.Blog',
        on_delete=models.CASCADE,
        related_name='audio_files'
    )

    # Audio configuration
    mode = models.CharField(
        max_length=20,
        choices=MODE_CHOICES,
        default='explain',
        help_text="Audio transformation mode"
    )
    language = models.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default='en',
        help_text="Audio language"
    )
    understanding_level = models.CharField(
        max_length=15,
        choices=UNDERSTANDING_LEVEL_CHOICES,
        default='intermediate',
        help_text="Content complexity level"
    )
    mood = models.CharField(
        max_length=20,
        choices=MOOD_CHOICES,
        default='educational',
        help_text="Voice style/mood"
    )

    # Generated content
    audio_file = models.FileField(
        upload_to=audio_file_path,
        null=True,
        blank=True,
        help_text="Generated audio file (MP3)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Audio generation status"
    )
    duration_seconds = models.IntegerField(
        default=0,
        help_text="Audio duration in seconds"
    )
    sections = models.JSONField(
        default=dict,
        help_text="Section timestamps: {intro: {start, end}, main: {...}, conclusion: {...}}"
    )
    transcript = models.TextField(
        default='',
        help_text="Full transcript of the audio"
    )
    summary = models.TextField(
        default='',
        help_text="AI-generated summary"
    )
    suggestions = models.JSONField(
        default=list,
        help_text="AI suggestions for other modes/languages"
    )
    questions = models.JSONField(
        default=list,
        help_text="AI-generated comprehension questions"
    )
    error_message = models.TextField(
        default='',
        blank=True,
        help_text="Error message if generation failed"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Audio file expiration time (for cleanup)"
    )
    download_count = models.IntegerField(default=0)

    class Meta:
        # One audio file per unique combination
        unique_together = ['blog', 'mode', 'language', 'understanding_level', 'mood']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['blog', 'mode', 'language'], name='audio_blog_mode_lang_idx'),
            models.Index(fields=['status', 'created_at'], name='audio_status_created_idx'),
        ]

    def __str__(self):
        return f"Audio for '{self.blog.title}' - {self.mode} ({self.language})"

    def save(self, *args, **kwargs):
        # Set expiration to 7 days from creation
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    @property
    def audio_url(self):
        """Return the URL to the audio file"""
        if self.audio_file and hasattr(self.audio_file, 'url'):
            return self.audio_file.url
        return None

    @property
    def is_ready(self):
        """Check if audio is ready for playback"""
        return self.status == 'ready' and self.audio_file


class UserAudioPreference(models.Model):
    """
    User preferences for audio playback and defaults.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='audio_preferences'
    )

    # Default preferences
    default_mode = models.CharField(
        max_length=20,
        choices=AudioFile.MODE_CHOICES,
        default='explain',
        help_text="User's preferred audio mode"
    )
    default_language = models.CharField(
        max_length=5,
        choices=AudioFile.LANGUAGE_CHOICES,
        default='en',
        help_text="User's preferred language"
    )
    default_understanding_level = models.CharField(
        max_length=15,
        choices=AudioFile.UNDERSTANDING_LEVEL_CHOICES,
        default='intermediate',
        help_text="User's preferred understanding level"
    )
    default_mood = models.CharField(
        max_length=20,
        choices=AudioFile.MOOD_CHOICES,
        default='educational',
        help_text="User's preferred voice mood"
    )
    default_speed = models.FloatField(
        default=1.0,
        help_text="Default playback speed (0.5 - 2.0)"
    )
    default_volume = models.FloatField(
        default=0.8,
        help_text="Default volume (0.0 - 1.0)"
    )

    # Playback settings
    autoplay = models.BooleanField(
        default=False,
        help_text="Auto-play audio when blog loads"
    )
    highlight_sync_enabled = models.BooleanField(
        default=True,
        help_text="Enable text highlighting sync during playback"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Audio Preference"
        verbose_name_plural = "User Audio Preferences"

    def __str__(self):
        return f"Audio preferences for {self.user.username}"


class AudioQuestion(models.Model):
    """
    AI-generated comprehension questions for audio content.
    """
    QUESTION_TYPES = [
        ('recall', 'Recall - Tests memory of key facts'),
        ('understand', 'Understand - Tests comprehension'),
        ('apply', 'Apply - Tests application of concepts'),
        ('analyze', 'Analyze - Tests critical thinking'),
    ]

    audio_file = models.ForeignKey(
        AudioFile,
        on_delete=models.CASCADE,
        related_name='audio_questions'
    )

    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES,
        default='understand'
    )
    question = models.TextField(help_text="The question text")
    options = models.JSONField(
        default=list,
        help_text="Multiple choice options for this question"
    )
    correct_answer = models.CharField(
        max_length=500,
        help_text="The correct answer"
    )
    explanation = models.TextField(
        blank=True,
        help_text="Explanation of the correct answer"
    )
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Question for {self.audio_file.blog.title}: {self.question[:50]}..."