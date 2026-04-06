"""
Celery Tasks for Audio Generation

Handles async audio generation, cleanup, and notification.
"""
import json
import logging
import os
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_blog_audio_task(self, audio_file_id: int):
    """
    Generate audio for a blog asynchronously.

    This task:
    1. Retrieves the AudioFile record
    2. Gets the blog content
    3. Transforms content via AI
    4. Generates audio via TTS
    5. Saves the audio file
    6. Sends MQTT notification

    Args:
        audio_file_id: ID of the AudioFile record to process

    Returns:
        dict with status and result information
    """
    # Import here to avoid circular imports
    from .models import AudioFile
    from .services import get_audio_service, AudioGenerationConfig

    logger.info(f"Starting audio generation task for AudioFile {audio_file_id}")

    try:
        audio_file = AudioFile.objects.select_related('blog').get(id=audio_file_id)
    except AudioFile.DoesNotExist:
        logger.error(f"AudioFile {audio_file_id} not found")
        return {'status': 'error', 'message': 'AudioFile not found'}

    # Update status to processing
    audio_file.status = 'processing'
    audio_file.save(update_fields=['status', 'updated_at'])

    try:
        # Get the blog
        blog = audio_file.blog

        # Prepare configuration
        config = AudioGenerationConfig(
            mode=audio_file.mode,
            language=audio_file.language,
            understanding_level=audio_file.understanding_level,
            mood=audio_file.mood,
        )

        # Generate audio
        audio_service = get_audio_service()
        audio_bytes, generated_content = audio_service.generate_audio(
            blog_content=blog.content,
            blog_title=blog.title,
            config=config,
        )

        # Save audio file
        output_extension = getattr(generated_content, "file_extension", "mp3") or "mp3"
        filename = f"blog_{blog.id}_{audio_file.mode}_{audio_file.language}.{output_extension}"
        audio_file.audio_file.save(
            filename,
            ContentFile(audio_bytes),
            save=False
        )

        # Update AudioFile with results
        audio_file.status = 'ready'
        audio_file.duration_seconds = generated_content.sections.get('conclusion', {}).get('end', 0)
        audio_file.sections = generated_content.sections
        audio_file.transcript = generated_content.transcript
        audio_file.summary = generated_content.summary
        audio_file.suggestions = generated_content.suggestions
        audio_file.save()

        # Send MQTT notification
        _send_audio_ready_notification(blog.id, audio_file.id)

        logger.info(f"Audio generation complete for AudioFile {audio_file_id}")

        return {
            'status': 'success',
            'audio_file_id': audio_file_id,
            'duration_seconds': audio_file.duration_seconds,
        }

    except Exception as e:
        logger.error(f"Audio generation failed for AudioFile {audio_file_id}: {e}")

        # Update status to failed
        audio_file.status = 'failed'
        audio_file.error_message = str(e)[:500]
        audio_file.save(update_fields=['status', 'error_message', 'updated_at'])

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        return {
            'status': 'error',
            'audio_file_id': audio_file_id,
            'message': str(e),
        }


@shared_task
def cleanup_old_audio_files_task():
    """
    Clean up expired audio files.

    Audio files have an expiration date to manage storage.
    This task removes files past their expiration.
    """
    from .models import AudioFile

    logger.info("Starting audio file cleanup")

    # Find expired audio files
    expired_files = AudioFile.objects.filter(
        expires_at__lt=timezone.now()
    )

    deleted_count = 0

    for audio_file in expired_files:
        try:
            # Delete the physical file
            if audio_file.audio_file:
                storage_path = audio_file.audio_file.path
                if os.path.exists(storage_path):
                    os.remove(storage_path)
                    logger.debug(f"Deleted file: {storage_path}")

            # Delete the database record
            audio_file.delete()
            deleted_count += 1

        except Exception as e:
            logger.error(f"Error deleting AudioFile {audio_file.id}: {e}")

    logger.info(f"Cleanup complete. Deleted {deleted_count} expired audio files.")

    return {'deleted_count': deleted_count}


@shared_task
def generate_questions_for_audio_task(audio_file_id: int, num_questions: int = 3):
    """
    Generate comprehension questions for an audio file.

    Args:
        audio_file_id: ID of the AudioFile
        num_questions: Number of questions to generate

    Returns:
        dict with generated questions
    """
    from .models import AudioFile, AudioQuestion
    from .services import get_audio_service

    logger.info(f"Generating questions for AudioFile {audio_file_id}")

    try:
        audio_file = AudioFile.objects.get(id=audio_file_id)

        if not audio_file.transcript:
            return {'status': 'error', 'message': 'No transcript available'}

        # Generate questions
        audio_service = get_audio_service()
        questions = audio_service.generate_questions(
            transcript=audio_file.transcript,
            num_questions=num_questions,
        )

        # Save questions to database
        for idx, q in enumerate(questions):
            AudioQuestion.objects.create(
                audio_file=audio_file,
                question_type=q.get('type', 'understand'),
                question=q.get('question', ''),
                options=q.get('options', []),
                correct_answer=q.get('correct_answer', ''),
                explanation=q.get('explanation', ''),
                order=idx,
            )

        # Update audio file with question references
        audio_file.questions = questions
        audio_file.save(update_fields=['questions'])

        logger.info(f"Generated {len(questions)} questions for AudioFile {audio_file_id}")

        return {
            'status': 'success',
            'questions_count': len(questions),
        }

    except AudioFile.DoesNotExist:
        return {'status': 'error', 'message': 'AudioFile not found'}
    except Exception as e:
        logger.error(f"Question generation failed: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def reexplain_audio_section_task(audio_file_id: int, section: str):
    """
    Generate a re-explanation for a specific section.

    Args:
        audio_file_id: ID of the AudioFile
        section: Section to re-explain (intro, main, conclusion)

    Returns:
        dict with the re-explanation text
    """
    from .models import AudioFile
    from .services import get_audio_service, AudioGenerationConfig

    logger.info(f"Re-explaining {section} section for AudioFile {audio_file_id}")

    try:
        audio_file = AudioFile.objects.select_related('blog').get(id=audio_file_id)

        if not audio_file.transcript:
            return {'status': 'error', 'message': 'No transcript available'}

        # Prepare configuration
        config = AudioGenerationConfig(
            mode=audio_file.mode,
            language=audio_file.language,
            understanding_level=audio_file.understanding_level,
            mood=audio_file.mood,
        )

        # Generate re-explanation
        audio_service = get_audio_service()
        reexplained_text = audio_service.reexplain_section(
            transcript=audio_file.transcript,
            section=section,
            blog_content=audio_file.blog.content,
            config=config,
        )

        logger.info(f"Re-explanation complete for AudioFile {audio_file_id}")

        return {
            'status': 'success',
            'section': section,
            'text': reexplained_text,
        }

    except AudioFile.DoesNotExist:
        return {'status': 'error', 'message': 'AudioFile not found'}
    except Exception as e:
        logger.error(f"Re-explanation failed: {e}")
        return {'status': 'error', 'message': str(e)}


def _send_audio_ready_notification(blog_id: int, audio_file_id: int):
    """
    Send MQTT notification that audio is ready.

    Args:
        blog_id: ID of the blog
        audio_file_id: ID of the generated AudioFile
    """
    try:
        from myproject.mqtt_client import publish_message

        publish_message(
            f"audio/ready/{blog_id}",
            json.dumps({
                'blog_id': blog_id,
                'audio_file_id': audio_file_id,
                'status': 'ready',
                'timestamp': timezone.now().isoformat(),
            })
        )

        logger.info(f"Sent audio ready notification for blog {blog_id}")

    except Exception as e:
        logger.warning(f"Failed to send MQTT notification: {e}")
        # Don't fail the task if notification fails
        pass


@shared_task
def pregenerate_popular_audio_task():
    """
    Pre-generate audio for popular blogs.

    This task can be run on a schedule to pre-generate
    audio for frequently accessed blogs to improve
    user experience by reducing wait times.

    Configuration (in settings.py):
        AUDIO_PREGENERATION_LIMIT: Number of popular blogs to process
        AUDIO_PREGENERATION_MODES: List of modes to pre-generate
        AUDIO_PREGENERATION_LANGUAGES: List of languages to pre-generate
    """
    from .models import AudioFile
    from django.db.models import Count

    limit = getattr(settings, 'AUDIO_PREGENERATION_LIMIT', 10)
    modes = getattr(settings, 'AUDIO_PREGENERATION_MODES', ['explain', 'summary'])
    languages = getattr(settings, 'AUDIO_PREGENERATION_LANGUAGES', ['en'])

    logger.info(f"Pre-generating audio for top {limit} blogs")

    try:
        # Find most viewed/downloaded blogs (customize query based on your metrics)
        from blog_app.models import Blog

        # Get published blogs ordered by creation date (or use a popularity metric)
        popular_blogs = Blog.objects.filter(
            is_published=True
        ).order_by('-created_at')[:limit]

        generated_count = 0

        for blog in popular_blogs:
            for mode in modes:
                for language in languages:
                    # Check if audio already exists
                    exists = AudioFile.objects.filter(
                        blog=blog,
                        mode=mode,
                        language=language,
                        status='ready'
                    ).exists()

                    if not exists:
                        # Queue generation task
                        audio_file = AudioFile.objects.create(
                            blog=blog,
                            mode=mode,
                            language=language,
                            status='pending'
                        )
                        generate_blog_audio_task.delay(audio_file.id)
                        generated_count += 1

        logger.info(f"Queued {generated_count} audio generation tasks")
        return {'queued_count': generated_count}

    except Exception as e:
        logger.error(f"Pre-generation task failed: {e}")
        return {'error': str(e)}
