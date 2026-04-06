# 🎧 Smart Audio Blog - Frontend Setup Guide

## Quick Start (3 Steps)

### 1. Apply Backend Configuration

Ensure you've completed the backend integration in `audio-integration-summary.md`:
- ✓ Audio app registered in `settings.py`
- ✓ Migrations applied
- ✓ Dependencies installed
- ✓ URLs integrated

### 2. Collect Static Files

```bash
cd "/home/ss/Ayush SS/Ayush Coding/Django-DRF-Blog-Application/myproject"

# If DEBUG=True, static files served automatically
# For production or to verify:
python manage.py collectstatic --noinput
```

### 3. Access the Audio Hub

#### Option A: Direct Access
```
http://localhost:8000/audio-hub/?blog_id=1
```
(Replace `1` with an actual published blog ID)

#### Option B: From Blog Detail
Add this button to your blog detail template:

```django
{% if blog.is_published %}
  <a href="{% url 'audio-hub' %}?blog_id={{ blog.id }}" class="audio-btn audio-btn-primary">
    <span class="material-icons">headphones</span>
    Listen to Audio
  </a>
{% endif %}
```

---

## 🎨 UI Components

### 1. Audio Generation Card

**Location:** `audio_hub.html` lines 44-87

Users can select:
- **Mode**: Explain, Conversation, Summary
- **Language**: English, Hindi, Gujarati
- **Level**: Beginner, Intermediate, Expert
- **Mood**: Educational, Serious, Storytelling

**Usage:** Automatically displayed when visiting `/audio-hub/`

### 2. Custom Audio Player

**Features:**
- Play/Pause with large button
- Seek by clicking progress bar
- Skip forward/backward 10 seconds
- Add bookmark at current position
- Displays current time and total duration

**Customization:** Modify `audio-app.js` `renderPlayer()` method (lines 308-370)

### 3. User Preferences Panel

**Settings:**
- Default audio mode/language/level/mood
- Playback speed (0.5x - 2.0x)
- Default volume (0-100%)
- Autoplay toggle
- Text-sync highlight toggle

**Persistence:** Automatically saved to `/api/audio/preferences/`

### 4. Bookmarks

**Functionality:**
- Add bookmark during playback (🔖 button)
- Jump to bookmark time
- Delete bookmarks
- Title and note support

**Storage:** `/api/audio/bookmarks/` API

### 5. Comprehension Questions

**Features:**
- Generate 1-10 questions per audio
- Multiple choice format
- Instant feedback (correct/incorrect)
- Explanations for answers

**Generate:** Click "Generate Questions" button

---

## 🎯 Integration Examples

### Example 1: Add Audio Button to Existing Blog Template

```django
{% extends 'base.html' %}
{% load static %}

{% block content %}
<article class="blog-post">
  <h1>{{ blog.title }}</h1>
  <div class="meta">
    By {{ blog.author }} | {{ blog.published_at|date:"M d, Y" }}
  </div>

  {% if blog.image %}
    <img src="{{ blog.image.url }}" alt="{{ blog.title }}" class="blog-image">
  {% endif %}

  <div class="blog-content">
    {{ blog.content|safe }}
  </div>

  <!-- Audio Hub Button -->
  <div style="text-align: center; margin: 40px 0;">
    <a href="{% url 'audio-hub' %}?blog_id={{ blog.id }}" class="audio-btn audio-btn-primary" style="font-size: 1.2rem; padding: 16px 32px;">
      <span class="material-icons" style="font-size: 1.5rem; vertical-align: middle;">headphones</span>
      🎧 Listen to This Article
    </a>
    <p style="color: var(--md-text-secondary); margin-top: 12px;">
      Transform this blog into audio with AI-powered narration
    </p>
  </div>
</article>
{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{% static 'audio/css/audio-styles.css' %}">
{% endblock %}
```

### Example 2: Embed Audio Hub in Modal

```html
<!-- Button to open modal -->
<button onclick="openAudioModal()">Open Audio</button>

<!-- Modal (hidden by default) -->
<div id="audio-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 9999;">
  <div style="background: white; margin: 5% auto; padding: 0; max-width: 90%; max-height: 90vh; overflow-y: auto; border-radius: 12px;">
    <div style="padding: 16px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eee;">
      <h3 style="margin: 0;">Audio Hub</h3>
      <button onclick="closeAudioModal()" style="border: none; background: none; font-size: 1.5rem; cursor: pointer;">&times;</button>
    </div>
    <iframe src="/audio-hub/?blog_id={{ blog.id }}" style="width: 100%; height: 80vh; border: none;"></iframe>
  </div>
</div>

<script>
function openAudioModal() {
  document.getElementById('audio-modal').style.display = 'block';
}
function closeAudioModal() {
  document.getElementById('audio-modal').style.display = 'none';
}
</script>
```

### Example 3: Show Audio Status on Blog List

```javascript
// Fetch audio status for each blog in list
async function updateAudioStatus(blogId, element) {
  try {
    const response = await fetch(`/api/blogs/${blogId}/audio/status/?mode=explain&language=en`);
    const data = await response.json();

    if (data.status === 'ready') {
      element.innerHTML = '<span class="audio-status audio-status-ready">✓ Audio Ready</span>';
      element.onclick = () => window.location.href = `/audio-hub/?blog_id=${blogId}`;
    } else if (data.status === 'processing') {
      element.innerHTML = '<span class="audio-status audio-status-processing">Generating...</span>';
    }
  } catch (error) {
    // No audio available
  }
}
```

---

## 🔧 Customization

### Change Theme Colors

Edit `blog_app/static/audio/css/audio-styles.css`:

```css
:root {
  --md-primary: #6200EE; /* Purple */
  --md-primary-dark: #3700B3;
  --md-secondary: #03DAC6; /* Teal */
}
```

### Add Custom Audio Modes

1. **Backend** (`blog_app/audio/models.py`):
```python
MODE_CHOICES = [
    ...existing choices...,
    ('custom', 'Custom Mode'),
]
```

2. **Frontend** (template):
```html
<option value="custom">🌟 Custom Mode</option>
```

3. **TTS Service** (`services.py`): Add mode handling in `_transform_content()`

### Modify Player Layout

The player is rendered dynamically in `audio-app.js` `renderPlayer()` method.

To add extra controls:

```javascript
renderPlayer(response) {
  const playerContainer = document.getElementById('audio-player-container');
  playerContainer.innerHTML = `
    <!-- existing HTML -->
    <button class="audio-control-btn" id="custom-btn" title="Custom Action">
      ⭐
    </button>
    <!-- existing HTML -->
  `;

  // Add event listener
  document.getElementById('custom-btn').addEventListener('click', () => {
    // Your custom action
  });
}
```

---

## 🐛 Troubleshooting

### Problem: Audio player not showing

**Check:**
1. Open browser DevTools → Console for errors
2. Verify API response includes `audio_url`
3. Check Network tab for 404 on audio file
4. Ensure MEDIA_URL is configured and media files are accessible

### Problem: "403 Forbidden" on API calls

**Fix:**
1. Ensure user is logged in
2. Verify JWT token in localStorage: `localStorage.getItem('access_token')`
3. Check token hasn't expired (default: 24 hours)
4. Implement token refresh if needed

### Problem: Audio generation never completes

**Check:**
1. Is Celery worker running? (`celery -A myproject worker -l info`)
2. Are `ANTHROPIC_API_KEY` and `GOOGLE_APPLICATION_CREDENTIALS` set?
3. Check Celery logs for errors
4. Verify Google Cloud TTS API quota not exceeded

### Problem: Static files not loading

**Fix:**
```bash
# Development
python manage.py runserver

# Ensure STATIC_URL and STATIC_ROOT in settings.py
# Ensure DEBUG = True for automatic static serving

# Production
python manage.py collectstatic
# Configure Nginx/Apache to serve from STATIC_ROOT
```

### Problem: CORS errors in production

**Fix:** Add `django-cors-headers`:

```python
# settings.py
INSTALLED_APPS = [
    ...,
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    ...,
]

CORS_ALLOWED_ORIGINS = [
    "https://your-frontend-domain.com",
]
```

---

## 📱 Mobile Optimization

The UI is fully responsive, but you can enhance mobile experience:

1. **Add to Home Screen** (PWA):
   - Add `manifest.json` and service worker
   - `<link rel="manifest" href="{% static 'audio/manifest.json' %}">`

2. **Touch Controls:**
   - Increase button size to 56px minimum (already 64px play/pause)
   - Add haptic feedback: `navigator.vibrate(50)`

3. **Optimize Images:**
   - Convert SVG icons to inline (already done)
   - Lazy load images with `loading="lazy"`

---

## 🎯 Performance Tips

1. **Lazy Load Audio App:** Only load `audio-app.js` on audio-hub page, not globally.

2. **Prefetch Audio Files:**
```javascript
// After audio generation completes
if (audio_url) {
  const link = document.createElement('link');
  link.rel = 'preload';
  link.as = 'audio';
  link.href = audio_url;
  document.head.appendChild(link);
}
```

3. **Cache Preferences Locally:**
```javascript
// Already handled by localStorage in JWT system
// Could add cache-busting for API calls
const cacheKey = `audio_prefs_${userId}`;
localStorage.setItem(cacheKey, JSON.stringify(prefs));
```

4. **Optimize Images:**
   - SVG icons are already lightweight
   - Blog images should be optimized server-side

---

## 📊 Analytics Tracking

Add tracking for user interactions:

```javascript
// In audio-app.js, add to generateAudio():
gtag('event', 'audio_generate', {
  'event_category': 'audio',
  'event_label': mode + '_' + language,
  'value': blog_id
});

// In togglePlayPause():
gtag('event', 'audio_play', {
  'event_category': 'audio',
  'audio_id': this.currentAudio.id
});
```

---

## 🌐 Multi-language Support

The UI currently supports:
- English (default)
- Hindi (हिंदी) - via Google TTS
- Gujarati (ગુજરાતી) - via Google TTS

To add UI translations:

1. Create translation files:
```bash
django-admin makemessages -l hi
django-admin makemessages -l gu
```

2. Wrap strings in templates:
```django
{% trans "Generate Audio" %}
{% trans "Audio Player" %}
```

3. JavaScript: Use Django's i18n in templates:
```javascript
const messages = {
  play: "{% trans 'Play' %}",
  pause: "{% trans 'Pause' %}",
};
```

---

## 🔒 Security

✅ **CSRF Protection:** Django's CSRF token used in forms
✅ **XSS Prevention:** `escapeHtml()` function sanitizes all dynamic content
✅ **Authentication:** JWT required for all user-specific endpoints
✅ **Authorization:** Backend validates user access to blogs/audio

**Additional recommendations:**
- Rate limit audio generation (5 per minute)
- Validate audio file size before download
- Use HTTPS in production for audio streaming

---

## 🎉 Success Checklist

- [ ] Audio hub loads at `/audio-hub/?blog_id=X`
- [ ] Blog title/excerpt displays correctly
- [ ] Can select mode/language/level/mood
- [ ] Generate button creates audio task
- [ ] Status updates to "Ready" after generation
- [ ] Audio player appears and plays audio
- [ ] Playback controls work (play/pause, seek, skip)
- [ ] Bookmark button adds bookmark
- [ ] Preferences panel loads and saves
- [ ] Bookmarks list displays
- [ ] Questions generate and display
- [ ] UI is responsive on mobile
- [ ] Styling matches Material Design
- [ ] No console errors in browser DevTools

---

## 📞 Support

If you encounter issues:

1. Check browser DevTools Console and Network tabs
2. Verify backend API is running and accessible
3. Check Django logs for server errors
4. Ensure all migrations are applied
5. Confirm user has access to the blog

**Common issues resolved quickly:**
- 404 on static files → Run `collectstatic`
- 401 on API → Check JWT token
- Audio not playing → Check CORS for media files
- Generation stuck → Start Celery worker

---

**✨ Enjoy your beautiful Smart Audio Blog interface!**
