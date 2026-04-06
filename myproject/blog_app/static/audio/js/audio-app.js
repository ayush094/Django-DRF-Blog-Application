/**
 * Smart Audio Blog - Frontend Application
 * Handles audio generation, playback, preferences, and questions
 */

class AudioBlogApp {
  constructor() {
    this.apiBase = '/api';
    this.csrfToken = this.getCsrfToken();
    this.currentAudio = null;
    this.audioPlayer = null;
    this.isPlaying = false;
    this.currentTime = 0;
    this.duration = 0;
    this.playbackInterval = null;

    this.init();
  }

  /**
   * Initialize the application
   */
  init() {
    this.setupEventListeners();
    this.loadUserPreferences();
    this.loadBlogAudioList();

    // Check URL parameters for direct audio playback
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('audio_id')) {
      this.playAudioById(parseInt(urlParams.get('audio_id')));
    }
  }

  /**
   * Get CSRF token from cookies
   */
  getCsrfToken() {
    const name = 'csrftoken';
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  }

  /**
   * Make authenticated API request
   */
  async apiRequest(endpoint, method = 'GET', body = null) {
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    if (!this.isPublicEndpoint(endpoint)) {
      const token = localStorage.getItem('access_token');
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      } else {
        throw new Error('Authentication required. Please log in.');
      }
    }

    const config = {
      method,
      headers,
    };

    if (body) {
      config.body = JSON.stringify(body);
    }

    const response = await fetch(`${this.apiBase}${endpoint}`, config);

    if (response.status === 401) {
      this.showAlert('Session expired. Please log in again.', 'error');
      this.logout();
      throw new Error('Unauthorized');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || 'Request failed');
    }

    return response.json();
  }

  /**
   * Check if endpoint is public (no auth required)
   */
  isPublicEndpoint(endpoint) {
    return endpoint.startsWith('/blogs/') && endpoint.includes('/audio/');
  }

  /**
   * Setup event listeners for dynamic elements
   */
  setupEventListeners() {
    // Audio generation form
    const generateForm = document.getElementById('audio-generate-form');
    if (generateForm) {
      generateForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.generateAudio();
      });
    }

    // Status check button
    const statusBtn = document.getElementById('check-status-btn');
    if (statusBtn) {
      statusBtn.addEventListener('click', () => this.checkAudioStatus());
    }

    // Preferences form
    const preferencesForm = document.getElementById('preferences-form');
    if (preferencesForm) {
      preferencesForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.savePreferences();
      });
    }

    // Progress bar click
    const progressBar = document.getElementById('audio-progress-bar');
    if (progressBar) {
      progressBar.addEventListener('click', (e) => this.seekAudio(e));
    }

    // Questions form
    const questionsForm = document.getElementById('questions-form');
    if (questionsForm) {
      questionsForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.submitAnswer();
      });
    }
  }

  /**
   * Generate audio for current blog
   */
  async generateAudio() {
    const blogId = this.getBlogId();
    if (!blogId) {
      this.showAlert('Blog ID not found', 'error');
      return;
    }

    const formData = {
      mode: document.getElementById('id_mode').value,
      language: document.getElementById('id_language').value,
      understanding_level: document.getElementById('id_understanding_level').value,
      mood: document.getElementById('id_mood').value,
    };

    const btn = document.getElementById('generate-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="audio-spinner" style="width:20px;height:20px;border-width:2px;margin:0;"></span> Generating...';

    try {
      const response = await this.apiRequest(
        `/blogs/${blogId}/audio/generate/`,
        'POST',
        formData
      );

      this.showAlert(response.message, 'success');

      if (response.status === 'ready') {
        this.loadAudioPlayer(response.audio_id);
      } else if (response.status === 'pending') {
        this.showGenerationProgress(response.audio_id);
      }
    } catch (error) {
      this.showAlert(error.message, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = 'Generate Audio';
    }
  }

  /**
   * Check audio generation status
   */
  async checkAudioStatus() {
    const blogId = this.getBlogId();
    if (!blogId) return;

    const params = new URLSearchParams({
      mode: document.getElementById('id_mode').value,
      language: document.getElementById('id_language').value,
      understanding_level: document.getElementById('id_understanding_level').value,
      mood: document.getElementById('id_mood').value,
    });

    try {
      const response = await this.apiRequest(
        `/blogs/${blogId}/audio/status/?${params.toString()}`,
        'GET'
      );

      this.displayStatus(response);
    } catch (error) {
      this.showAlert(error.message, 'error');
    }
  }

  /**
   * Display audio status
   */
  displayStatus(response) {
    const statusEl = document.getElementById('audio-status');
    const progressEl = document.getElementById('audio-generation-progress');

    if (response.status === 'ready') {
      statusEl.innerHTML = `
        <span class="audio-status audio-status-ready">
          ✓ Ready
        </span>
      `;
      if (progressEl) progressEl.style.display = 'none';
      this.loadAudioPlayer(response.audio_id);
    } else if (response.status === 'processing') {
      statusEl.innerHTML = `
        <span class="audio-status audio-status-processing">
          Processing... ${response.progress || 50}%
        </span>
      `;
      if (progressEl) progressEl.style.display = 'block';
    } else if (response.status === 'pending') {
      statusEl.innerHTML = `
        <span class="audio-status audio-status-pending">
          Queued...
        </span>
      `;
      if (progressEl) progressEl.style.display = 'block';
    } else if (response.status === 'failed') {
      statusEl.innerHTML = `
        <span class="audio-status audio-status-failed">
          ✗ Failed
        </span>
      `;
      this.showAlert(response.message || 'Audio generation failed', 'error');
      if (progressEl) progressEl.style.display = 'none';
    } else {
      statusEl.innerHTML = `
        <span class="audio-status audio-status-pending">
          Not Found
        </span>
      `;
      if (progressEl) progressEl.style.display = 'none';
    }
  }

  /**
   * Show generation progress polling
   */
  showGenerationProgress(audioId) {
    const statusEl = document.getElementById('audio-status');
    const progressEl = document.getElementById('audio-generation-progress');

    if (progressEl) progressEl.style.display = 'block';

    const pollInterval = setInterval(async () => {
      try {
        const response = await this.apiRequest(`/api/audio/files/${audioId}/status/`, 'GET');
        if (response.status === 'ready') {
          clearInterval(pollInterval);
          this.displayStatus(response);
          this.loadAudioPlayer(audioId);
        } else if (response.status === 'failed') {
          clearInterval(pollInterval);
          this.displayStatus(response);
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 3000);

    // Timeout after 2 minutes
    setTimeout(() => {
      clearInterval(pollInterval);
      if (progressEl) progressEl.style.display = 'none';
    }, 120000);
  }

  /**
   * Load audio player with given ID
   */
  async loadAudioPlayer(audioId) {
    try {
      const response = await this.apiRequest(`/api/audio/files/${audioId}/`, 'GET');

      this.currentAudio = response;
      this.duration = response.duration_seconds || 0;

      this.renderPlayer(response);

      if (response.audio_url) {
        this.audioPlayer = new Audio(response.audio_url);
        this.setupAudioEvents();
      }
    } catch (error) {
      console.error('Failed to load audio:', error);
    }
  }

  /**
   * Render audio player UI
   */
  renderPlayer(response) {
    const playerContainer = document.getElementById('audio-player-container');
    if (!playerContainer) return;

    playerContainer.innerHTML = `
      <div class="audio-player audio-fade-in">
        <div class="audio-player-header">
          <div class="audio-cover-art">
            🎙️
          </div>
          <div class="audio-player-info">
            <div class="audio-player-title">${this.escapeHtml(response.mode || 'Audio')}</div>
            <div class="audio-player-subtitle">
              ${this.escapeHtml(response.language)} • ${this.escapeHtml(response.understanding_level)} • ${this.escapeHtml(response.mood)}
            </div>
            <div style="margin-top: 8px;">
              <span class="audio-status audio-status-ready">Ready</span>
            </div>
          </div>
        </div>

        <div class="audio-progress-container">
          <div class="audio-progress" id="audio-progress-bar">
            <div class="audio-progress-bar" id="audio-progress-fill"></div>
          </div>
          <div class="audio-time">
            <span id="audio-current-time">0:00</span>
            <span id="audio-duration">${this.formatTime(this.duration)}</span>
          </div>
        </div>

        <div class="audio-controls">
          <button class="audio-control-btn" id="rewind-btn" title="Rewind 10s">
            ⏪
          </button>
          <button class="audio-control-btn play-pause" id="play-pause-btn" title="Play/Pause">
            ▶️
          </button>
          <button class="audio-control-btn" id="forward-btn" title="Forward 10s">
            ⏩
          </button>
        </div>
      </div>
    `;

    // Re-attach event listeners
    this.setupPlayerEvents();
  }

  /**
   * Setup audio player events
   */
  setupPlayerEvents() {
    const playPauseBtn = document.getElementById('play-pause-btn');
    const rewindBtn = document.getElementById('rewind-btn');
    const forwardBtn = document.getElementById('forward-btn');
    const progressBar = document.getElementById('audio-progress-bar');

    if (playPauseBtn) {
      playPauseBtn.addEventListener('click', () => this.togglePlayPause());
    }

    if (rewindBtn) {
      rewindBtn.addEventListener('click', () => this.skip(-10));
    }

    if (forwardBtn) {
      forwardBtn.addEventListener('click', () => this.skip(10));
    }

    if (progressBar && this.audioPlayer) {
      progressBar.addEventListener('click', (e) => this.seekAudio(e));
    }
  }

  /**
   * Setup Audio element events
   */
  setupAudioEvents() {
    if (!this.audioPlayer) return;

    this.audioPlayer.addEventListener('timeupdate', () => this.updateProgress());
    this.audioPlayer.addEventListener('loadedmetadata', () => {
      this.duration = this.audioPlayer.duration;
      this.updateDuration();
    });
    this.audioPlayer.addEventListener('ended', () => this.onAudioEnded());
    this.audioPlayer.addEventListener('play', () => {
      this.isPlaying = true;
      this.updatePlayPauseButton();
    });
    this.audioPlayer.addEventListener('pause', () => {
      this.isPlaying = false;
      this.updatePlayPauseButton();
    });
    this.audioPlayer.addEventListener('error', (e) => {
      this.showAlert('Failed to load audio file', 'error');
    });
  }

  /**
   * Toggle play/pause
   */
  togglePlayPause() {
    if (!this.audioPlayer) return;

    if (this.isPlaying) {
      this.audioPlayer.pause();
    } else {
      this.audioPlayer.play();
    }
  }

  /**
   * Skip forward/backward
   */
  skip(seconds) {
    if (!this.audioPlayer) return;
    this.audioPlayer.currentTime = Math.max(0, Math.min(this.audioPlayer.duration, this.audioPlayer.currentTime + seconds));
  }

  /**
   * Seek audio by clicking progress bar
   */
  seekAudio(event) {
    if (!this.audioPlayer || !this.audioPlayer.duration) return;

    const rect = event.currentTarget.getBoundingClientRect();
    const percent = (event.clientX - rect.left) / rect.width;
    this.audioPlayer.currentTime = percent * this.audioPlayer.duration;
  }

  /**
   * Update progress bar
   */
  updateProgress() {
    if (!this.audioPlayer || !this.audioPlayer.duration) return;

    const percent = (this.audioPlayer.currentTime / this.audioPlayer.duration) * 100;
    const fill = document.getElementById('audio-progress-fill');
    const currentTime = document.getElementById('audio-current-time');

    if (fill) fill.style.width = `${percent}%`;
    if (currentTime) currentTime.textContent = this.formatTime(this.audioPlayer.currentTime);
  }

  /**
   * Update duration display
   */
  updateDuration() {
    const durationEl = document.getElementById('audio-duration');
    if (durationEl) {
      durationEl.textContent = this.formatTime(this.duration);
    }
  }

  /**
   * Update play/pause button
   */
  updatePlayPauseButton() {
    const btn = document.getElementById('play-pause-btn');
    if (btn) {
      btn.textContent = this.isPlaying ? '⏸️' : '▶️';
    }
  }

  /**
   * Handle audio ended
   */
  onAudioEnded() {
    this.isPlaying = false;
    this.updatePlayPauseButton();
  }

  /**
   * Load user preferences
   */
  async loadUserPreferences() {
    try {
      const response = await this.apiRequest('/api/audio/preferences/', 'GET');
      this.populatePreferencesForm(response);

      const prefs = document.getElementById('user-preferences');
      if (prefs) prefs.style.display = 'block';
    } catch (error) {
      console.log('No preferences found, will create on save');
    }
  }

  /**
   * Populate preferences form
   */
  populatePreferencesForm(prefs) {
    const fields = [
      'default_mode', 'default_language', 'default_understanding_level',
      'default_mood', 'default_speed', 'default_volume', 'autoplay', 'highlight_sync_enabled'
    ];

    fields.forEach(field => {
      const input = document.getElementById(`id_${field}`);
      if (input && prefs[field] !== undefined) {
        input.value = prefs[field];
      }
    });
  }

  /**
   * Save user preferences
   */
  async savePreferences() {
    const formData = {
      default_mode: document.getElementById('id_default_mode').value,
      default_language: document.getElementById('id_default_language').value,
      default_understanding_level: document.getElementById('id_default_understanding_level').value,
      default_mood: document.getElementById('id_default_mood').value,
      default_speed: parseFloat(document.getElementById('id_default_speed').value),
      default_volume: parseFloat(document.getElementById('id_default_volume').value),
      autoplay: document.getElementById('id_autoplay').checked,
      highlight_sync_enabled: document.getElementById('id_highlight_sync_enabled').checked,
    };

    try {
      const response = await this.apiRequest('/api/audio/preferences/', 'PUT', formData);
      this.showAlert('Preferences saved!', 'success');
    } catch (error) {
      this.showAlert(error.message, 'error');
    }
  }

  /**
   * Load list of audio files for current blog
   */
  async loadBlogAudioList() {
    const blogId = this.getBlogId();
    if (!blogId) return;

    try {
      const response = await this.apiRequest(`/api/blogs/${blogId}/audio/list/`, 'GET');
      this.renderAudioList(response);
    } catch (error) {
      if (!error.message.includes('404')) {
        console.error('Failed to load audio list:', error);
      }
    }
  }

  /**
   * Render audio list
   */
  renderAudioList(audioList) {
    const listContainer = document.getElementById('audio-list-container');
    if (!listContainer) return;

    if (!audioList || audioList.length === 0) {
      listContainer.innerHTML = `
        <div class="audio-empty-state">
          <div class="audio-empty-state-icon">🎵</div>
          <h3>No Audio Generated Yet</h3>
          <p>Generate your first audio version of this blog above!</p>
        </div>
      `;
      return;
    }

    listContainer.innerHTML = audioList.map(audio => `
      <div class="audio-bookmark-item">
        <div class="audio-bookmark-time">${this.formatTime(audio.duration_seconds || 0)}</div>
        <div class="audio-bookmark-title">
          ${this.escapeHtml(audio.mode)} (${this.escapeHtml(audio.language)})
          <div style="font-size: 0.85rem; color: var(--md-text-secondary);">
            ${this.escapeHtml(audio.understanding_level)} • ${this.escapeHtml(audio.mood)}
          </div>
        </div>
        <button class="audio-btn audio-btn-secondary" onclick="audioApp.playAudioById(${audio.id})">
          Play
        </button>
        <button class="audio-btn audio-btn-secondary" onclick="audioApp.downloadAudio(${audio.id})">
          ⬇️
        </button>
      </div>
    `).join('');
  }

  /**
   * Play audio by ID
   */
  async playAudioById(audioId) {
    await this.loadAudioPlayer(audioId);
    if (this.audioPlayer) {
      this.audioPlayer.play();
    }
  }

  /**
   * Download audio file
   */
  async downloadAudio(audioId) {
    const blogId = this.getBlogId();
    if (!blogId) return;

    const response = await fetch(`${this.apiBase}/blogs/${blogId}/audio/${audioId}/download/`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    });

    if (response.ok) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `blog_${blogId}_audio_${audioId}.mp3`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } else {
      this.showAlert('Failed to download audio', 'error');
    }
  }

  /**
   * Load questions for audio
   */
  async loadQuestions() {
    const blogId = this.getBlogId();
    if (!blogId) return;

    try {
      const mode = document.getElementById('id_mode')?.value || 'explain';
      const params = new URLSearchParams({ mode });

      const response = await this.apiRequest(`/api/blogs/${blogId}/audio/questions/?${params.toString()}`, 'GET');
      this.renderQuestions(response);
    } catch (error) {
      if (!error.message.includes('404')) {
        console.error('Failed to load questions:', error);
      }
    }
  }

  /**
   * Render questions
   */
  renderQuestions(questions) {
    const container = document.getElementById('questions-container');
    if (!container) return;

    if (!questions || questions.length === 0) {
      container.innerHTML = `
        <div class="audio-empty-state">
          <div class="audio-empty-state-icon">❓</div>
          <h3>No Questions Yet</h3>
          <p>Generate comprehension questions to test your understanding!</p>
        </div>
      `;
      return;
    }

    container.innerHTML = questions.map((q, idx) => `
      <div class="audio-question" data-question-id="${q.id || idx}">
        <div class="audio-question-text">${idx + 1}. ${this.escapeHtml(q.question)}</div>
        <div class="audio-options">
          ${q.options.map((opt, optIdx) => `
            <label class="audio-option">
              <input type="radio" name="question_${idx}" value="${optIdx}" data-correct="${q.correct_answer === opt}">
              <span>${this.escapeHtml(opt)}</span>
            </label>
          `).join('')}
        </div>
        <div class="audio-question-feedback" style="margin-top: 12px; display: none;"></div>
        ${q.explanation ? `
          <div class="audio-question-explanation" style="margin-top: 12px; font-size: 0.9rem; color: var(--md-text-secondary);">
            💡 ${this.escapeHtml(q.explanation)}
          </div>
        ` : ''}
      </div>
    `).join('');

    // Add event listeners to options
    container.querySelectorAll('.audio-option input').forEach(input => {
      input.addEventListener('change', (e) => this.checkAnswer(e.target));
    });
  }

  /**
   * Check answer and show feedback
   */
  checkAnswer(input) {
    const questionDiv = input.closest('.audio-question');
    const feedback = questionDiv.querySelector('.audio-question-feedback');
    const isCorrect = input.dataset.correct === 'true';

    // Disable all options
    questionDiv.querySelectorAll('input').forEach(inp => {
      inp.disabled = true;
    });

    // Show feedback
    if (isCorrect) {
      feedback.textContent = '✓ Correct!';
      feedback.style.color = 'var(--md-success)';
      feedback.style.display = 'block';
    } else {
      feedback.textContent = '✗ Incorrect. Try again!';
      feedback.style.color = 'var(--md-error)';
      feedback.style.display = 'block';
    }

    // Highlight correct answer
    const correctInput = questionDiv.querySelector(`input[value="${Array.from(questionDiv.querySelectorAll('input')).find(i => i.dataset.correct === 'true')?.value}"]`);
    if (correctInput) {
      correctInput.parentElement.style.borderColor = 'var(--md-success)';
      correctInput.parentElement.style.background = '#E8F5E9';
    }
  }

  /**
   * Generate questions for audio
   */
  async generateQuestions() {
    const blogId = this.getBlogId();
    if (!blogId) return;

    const numQuestions = document.getElementById('id_num_questions')?.value || 3;

    try {
      await this.apiRequest(`/api/blogs/${blogId}/audio/questions/`, 'POST', {
        mode: document.getElementById('id_mode')?.value || 'explain',
        language: document.getElementById('id_language')?.value || 'en',
        understanding_level: document.getElementById('id_understanding_level')?.value || 'intermediate',
        mood: document.getElementById('id_mood')?.value || 'educational',
        num_questions: parseInt(numQuestions),
      });

      this.showAlert('Questions generated!', 'success');
      this.loadQuestions();
    } catch (error) {
      this.showAlert(error.message, 'error');
    }
  }

  /**
   * Show alert message
   */
  showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `audio-alert audio-alert-${type}`;
    alertDiv.innerHTML = `
      <span>${this.escapeHtml(message)}</span>
      <button onclick="this.parentElement.remove()" style="margin-left: auto; background: none; border: none; cursor: pointer; font-size: 1.2rem;">&times;</button>
    `;

    const container = document.querySelector('.audio-container');
    if (container) {
      container.insertBefore(alertDiv, container.firstChild);
      setTimeout(() => alertDiv.remove(), 5000);
    }
  }

  /**
   * Format seconds to MM:SS
   */
  formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Get blog ID from context
   */
  getBlogId() {
    const blogIdEl = document.getElementById('blog-id');
    return blogIdEl ? parseInt(blogIdEl.dataset.blogId) : null;
  }

  /**
   * Logout user
   */
  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/';
  }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.audioApp = new AudioBlogApp();
});
