# Audio Feature Completion Plan

## Context
The audio module (blog_app/audio) is fully developed with models, views, serializers, services, and Celery tasks, but it's not yet integrated into the Django project. The code exists but the module is not registered as an app, has no migrations, and its URLs are not connected to the main routing.

## Objectives
1. Register the audio module as a proper Django app
2. Create and apply database migrations for audio models
3. Integrate audio endpoints into URL routing
4. Add missing dependency (google-cloud-texttospeech)
5. Document environment configuration for Google TTS
6. Verify the feature works end-to-end

## Required Changes

### 1. Create Audio App Config
**File:** `blog_app/audio/apps.py`
```python
from django.apps import AppConfig

class AudioConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'blog_app.audio'
    verbose_name = "Smart Audio Blog Experience"
```

### 2. Register Audio App in Settings
**File:** `myproject/settings.py`
- Add `'blog_app.audio.apps.AudioConfig'` to `INSTALLED_APPS` after `'blog_app'`
- This will activate the audio models and migrations

### 3. Add Missing Dependency
**File:** `requirements.txt`
- Add: `google-cloud-texttospeech==2.23.0` (or latest stable version)

### 4. Create Audio Migrations
Run Django management commands:
```bash
python manage.py makemigrations blog_app.audio
python manage.py migrate
```

This will create:
- Initial migration for AudioFile, UserAudioPreference, AudioBookmark, AudioQuestion models

### 5. Integrate Audio URLs
**File:** `blog_app/urls.py`
- Import audio URLs: `from blog_app.audio import urls as audio_urls`
- Add two path entries:
  ```python
  # Blog-specific audio endpoints (nested under blogs)
  path('blogs/<int:blog_pk>/audio/', include(audio_urls.audio_blog_patterns)),

  # User audio preferences and bookmarks (top-level)
  path('audio/', include(audio_urls.urlpatterns)),
  ```
- Note: The blog_app/urls.py is mounted at `/api/` in main urls.py, so final paths will be:
  - `/api/blogs/{blog_pk}/audio/generate/`
  - `/api/blogs/{blog_pk}/audio/status/`
  - `/api/blogs/{blog_pk}/audio/` (GET)
  - `/api/blogs/{blog_pk}/audio/questions/`
  - `/api/blogs/{blog_pk}/audio/reexplain/`
  - `/api/blogs/{blog_pk}/audio/list/`
  - `/api/blogs/{blog_pk}/audio/{audio_id}/download/`
  - `/api/audio/preferences/` (GET, PUT)
  - `/api/audio/bookmarks/` (GET, POST, DELETE)

### 6. Document Google Cloud TTS Setup
**File:** `.env.example`
- Add: `GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json`
- Add note in comments about needing a Google Cloud service account with Text-to-Speech API enabled

**File:** Create `blog_app/audio/README.md` (optional but helpful)
- Document TTS setup, required environment variables, and usage examples

### 7. Verify Integration
After applying changes:
- Check that migrations are applied: `python manage.py showmigrations blog_app.audio`
- Test audio generation endpoint with authenticated user
- Verify audio file storage in media/audio/{blog_id}/
- Test MQTT notifications (if MQTT broker running)

## Dependencies & Prerequisites

### External Services
1. **Anthropic AI** - Already configured via `ANTHROPIC_API_KEY`
2. **Google Cloud Text-to-Speech** - Requires:
   - Service account key file
   - Environment variable `GOOGLE_APPLICATION_CREDENTIALS`
   - Enabled Text-to-Speech API in GCP project
3. **Celery** - Already configured (tasks.py defines async tasks)
4. **MQTT Broker** - For notifications (already in project)

### Environment Variables to Add
```
GOOGLE_APPLICATION_CREDENTIALS=/path/to/google-credentials.json
```

## Implementation Order
1. Create `apps.py` in audio directory
2. Update `settings.py` to register audio app
3. Update `requirements.txt` with google-cloud-texttospeech
4. Update `blog_app/urls.py` to include audio URLs
5. Update `.env.example` with Google credentials documentation
6. Run `makemigrations` and `migrate`
7. (Optional) Install new requirements: `pip install -r requirements.txt`
8. Test the endpoints

## Rollout Notes
- The audio feature is fully implemented but dormant; integration is straightforward
- No breaking changes to existing code
- Additive changes only (new URLs, new tables)
- Existing functionality remains unaffected
- Audio generation is async (Celery) so won't block main app

## Post-Implementation Verification
1. Swagger UI should show audio endpoints under "Audio", "Audio Preferences", "Audio Bookmarks" tags
2. POST to `/api/blogs/{id}/audio/generate/` should return audio_id with status "pending"
3. Celery worker must be running to process audio generation tasks
4. Audio files should be saved to `media/audio/{blog_id}/`
5. User can set preferences at `/api/audio/preferences/`
6. User can create bookmarks at `/api/audio/bookmarks/`

## Files to Modify
- `blog_app/audio/apps.py` (create)
- `myproject/settings.py` (add to INSTALLED_APPS)
- `requirements.txt` (add dependency)
- `blog_app/urls.py` (include audio URLs)
- `.env.example` (add GOOGLE_APPLICATION_CREDENTIALS)
- Optional: `blog_app/audio/README.md` (document setup)

## Testing Strategy
- Unit tests: Existing tests (if any) for audio module
- Integration: Use Swagger UI to test endpoints manually
- Verify database schema matches models
- Check that Celery tasks execute successfully (requires Google TTS credentials)
