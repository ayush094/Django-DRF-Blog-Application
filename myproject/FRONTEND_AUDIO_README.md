# Smart Audio Blog - Frontend UI Documentation

## 🎯 Overview

A beautiful, responsive, Material Design-inspired frontend for the Smart Audio Blog feature. This UI allows users to:

- Generate audio versions of blog posts in multiple languages and modes
- Play audio with a custom-styled player
- Manage user preferences (default mode, language, speed, volume, etc.)
- Bookmark important moments in audio
- Take comprehension quizzes
- View and manage all generated audio for a blog

## 🚀 Getting Started

### 1. Prerequisites

- Django project with audio app configured (see backend setup)
- Static files configured (`STATIC_URL`, `STATIC_ROOT`, `MEDIA_URL`, `MEDIA_ROOT`)
- User authentication system (JWT tokens)

### 2. Integration

#### Add URLs

The audio frontend is automatically added when you include the blog_app URLs. The main entry point is:

```
/audio-hub/?blog_id=<blog_id>
```

Optional parameters:
- `view=hub` - Full audio hub (default)
- `view=blog` - Blog detail page with audio embed

Example:
```
/audio-hub/?blog_id=1
/audio-hub/?blog_id=1&view=blog
```

#### Access from Blog Detail

To add an "Open Audio Hub" button to your blog detail page, add:

```html
<a href="{% url 'audio-hub' %}?blog_id={{ blog.id }}" class="audio-btn audio-btn-primary">
  <span class="material-icons">headphones</span>
  Audio Version
</a>
```

### 3. Static Files

The frontend assets are located in:
- CSS: `/static/audio/css/audio-styles.css`
- JS: `/static/audio/js/audio-app.js`

Make sure static files are properly served in development:
```bash
python manage.py collectstatic
```

Or in development with `DEBUG=True`, static files are served automatically.

## 🎨 Design System

### Colors (Material Design Inspired)

| Variable | Color | Usage |
|----------|-------|-------|
| `--md-primary` | `#1A73E8` | Primary brand color (Google Blue) |
| `--md-primary-dark` | `#0D47A1` | Hover states, active elements |
| `--md-primary-light` | `#E3F2FD` | Light backgrounds, highlights |
| `--md-secondary` | `#FF5722` | Accent calls-to-action |
| `--md-success` | `#4CAF50` | Success states |
| `--md-error` | `#F44336` | Error messages |
| `--md-surface` | `#FFFFFF` | Cards, containers |
| `--md-background` | `#F5F5F5` | Page background |

### Typography

- **Font Family:** Roboto (Google's Material Design font)
- **Headings:** 300/500 weight, responsive sizes
- **Body:** 400 weight, 1.6 line-height
- **Captions:** 500 weight, uppercase, 0.875rem

### Components

#### Cards
- White background (`--md-surface`)
- Border radius: 12px
- Box shadow: `0 2px 4px rgba(0,0,0,0.1)`
- Hover: shadow increase + slight translateY

#### Buttons
- Primary: filled, primary color, shadow
- Secondary: outlined, transparent background, colored border
- Icon buttons: circular, 48-64px
- All with 8px border radius

#### Forms
- Rounded inputs with 2px border
- Focus: primary color border + soft glow
- Custom Material Design toggle switches

#### Audio Player
- Cover art: circular gradient with microphone icon
- Progress bar: gradient fill, smooth seeking
- Controls: large circular buttons with icons
- Responsive: adapts to mobile screens

## 📋 Templates

### `audio_hub.html`

Main audio interface with all components:
- Blog info (optional, when `blog` context provided)
- Audio generation form (mode, language, level, mood)
- Audio status display with progress indicator
- Audio player with custom controls
- List of generated audio versions (play/download)
- Comprehension questions section
- User preferences panel (sidebar)
- Bookmarks panel (sidebar)
- Quick stats (sidebar)

**Context required:**
- `blog_id` (optional but recommended)
- `blog` object (optional, includes title and content excerpt)

**Template tags:**
```django
<!-- Blog ID for API calls -->
<div id="blog-id" data-blog-id="{{ blog_id }}"></div>

<!-- Blog info (optional) -->
{% if blog %}
  <div id="blog-info">
    <h2>{{ blog.title }}</h2>
    <p>{{ blog.content|truncatewords:50 }}</p>
  </div>
{% endif %}
```

### `blog_with_audio.html`

Blog detail page with embedded audio hub link/CTA. Use this when you want:
- Full blog article display
- Prominent "Open Audio Hub" call-to-action
- Option to embed audio directly

**Context required:**
- `blog` object (with title, content, image, author, published_at)

## 🔧 JavaScript API

The `AudioBlogApp` class provides all frontend functionality.

### Initialization

```javascript
// Auto-initializes on DOMContentLoaded
window.audioApp = new AudioBlogApp();
```

### Key Methods

| Method | Description |
|--------|-------------|
| `generateAudio()` | Submit generation request with current form values |
| `checkAudioStatus()` | Poll audio generation status |
| `loadAudioPlayer(audioId)` | Load and render audio player |
| `playAudioById(audioId)` | Play specific audio version |
| `loadUserPreferences()` | Fetch user's default settings |
| `savePreferences()` | Update user preferences |
| `loadBookmarks()` | Fetch user's bookmarks |
| `createBookmark(timestamp, title, note)` | Add new bookmark |
| `deleteBookmark(bookmarkId)` | Remove bookmark |
| `loadQuestions()` | Fetch comprehension questions |
| `generateQuestions()` | Generate new questions |
| `showAlert(message, type)` | Display alert (success/error/warning/info) |
| `formatTime(seconds)` | Convert seconds to MM:SS |

### Events

The app automatically sets up event listeners on:
- `#audio-generate-form` submit
- `#preferences-form` submit
- `#bookmark-form` submit
- Player controls (play/pause, skip, seek)
- Question option selection

### Customization

You can extend the app by overriding methods or adding event handlers:

```javascript
// Add custom event after audio loads
audioApp.audioPlayer.addEventListener('loadeddata', () => {
  console.log('Audio loaded, duration:', audioApp.audioPlayer.duration);
});

// Customize API base URL if needed
audioApp.apiBase = '/api/v2';
```

## 🔐 Authentication

The app expects JWT tokens stored in localStorage:
- `access_token` - for authenticated API calls

If token is missing or expired (401 response), the user is redirected to login.

To integrate with your auth system:

```javascript
// Set token after login
localStorage.setItem('access_token', response.access);

// Clear on logout
localStorage.removeItem('access_token');
localStorage.removeItem('refresh_token');
```

## 📱 Responsive Design

The UI is fully responsive with breakpoints:

- **Desktop:** 3-column layout (main + sidebar)
- **Tablet:** 2-column layout
- **Mobile:** 1-column stacked, optimized controls

Key responsive adjustments:
- Player controls: smaller buttons (48px vs 64px play/pause)
- Grid: switches to single column below 768px
- Padding: reduces on mobile
- Text sizes: slightly smaller on mobile

## 🎛️ Customization Guide

### Change Primary Color

Update CSS variables in `audio-styles.css`:

```css
:root {
  --md-primary: #YOUR_COLOR;
  --md-primary-dark: #YOUR_DARKER_SHADE;
  --md-primary-light: #YOUR_LIGHTER_SHADE;
}
```

### Add New Audio Modes

1. Update `AudioFile.MODE_CHOICES` in `models.py`
2. Add option to HTML select in template:
```html
<option value="your_mode">Your Mode Label</option>
```
3. Update JS validation if needed

### Add New Languages

1. Add to `AudioFile.LANGUAGE_CHOICES` in `models.py`
2. Add options in generation form:
```html
<option value="xx">Your Language</option>
```

### Customize Player Controls

Edit `audio-app.js` in `setupPlayerEvents()` method:
```javascript
// Add custom control
const customBtn = document.createElement('button');
customBtn.innerHTML = '🔁';
customBtn.addEventListener('click', () => {
  // Your custom action
});
document.querySelector('.audio-controls').appendChild(customBtn);
```

## 🐛 Debugging

### Common Issues

**Audio not playing:**
- Check browser console for CORS errors
- Verify `audio_url` is correct in network tab
- Ensure CORS headers are configured on backend

**Generation failed:**
- Check Celery worker logs
- Verify `ANTHROPIC_API_KEY` and `GOOGLE_APPLICATION_CREDENTIALS` are set
- Ensure Google TTS API is enabled

**401 Unauthorized:**
- Check JWT token in localStorage
- Token may have expired (default is 1 day for access token)
- Refresh token flow should be implemented

**Static files not loading:**
- Run `collectstatic` in production
- Check `STATIC_URL` and `STATIC_ROOT` in settings
- Verify Nginx/Apache static file configuration

### Dev Tools

Open browser DevTools and check:
- **Console:** JavaScript errors
- **Network:** API request/response status
- **Application > Storage:** localStorage tokens
- **Sources:** Set breakpoints in `audio-app.js`

## 🚀 Production Checklist

- [ ] Static files collected (`python manage.py collectstatic`)
- [ ] Nginx/Apache configured to serve static/media
- [ ] HTTPS enabled for secure audio streaming
- [ ] CORS configured (if separate frontend domain)
- [ ] JWT token rotation configured if needed
- [ ] Celery worker running for async audio generation
- [ ] Google Cloud TTS API quota sufficient
- [ ] Media storage (audio files) has sufficient disk space
- [ ] CDN configured for static assets (optional but recommended)

## 📚 API Endpoints Used

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/blogs/{id}/audio/generate/` | POST | Generate new audio |
| `/api/blogs/{id}/audio/status/` | GET | Check generation status |
| `/api/blogs/{id}/audio/` | GET | Get audio metadata |
| `/api/blogs/{id}/audio/{audio_id}/download/` | GET | Download MP3 |
| `/api/blogs/{id}/audio/list/` | GET | List all audio versions |
| `/api/blogs/{id}/audio/questions/` | POST | Generate questions |
| `/api/audio/preferences/` | GET/PUT | User preferences |
| `/api/audio/bookmarks/` | GET/POST/DELETE | Bookmark management |

All require authentication except those nested under blogs with published content (which can be accessed with proper permissions).

## 🎯 Browser Support

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+
- Mobile browsers (iOS Safari, Chrome Mobile)

Uses modern CSS (flexbox, grid, custom properties) and ES6 JavaScript.

## 📄 License

Part of the Django-DRF-Blog-Application project.

---

**Built with ❤️ using Material Design principles**
