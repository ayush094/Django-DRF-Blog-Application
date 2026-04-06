"""
URL Configuration for Smart Audio Blog Experience API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AudioViewSet, UserAudioPreferenceViewSet

# Create router for audio endpoints
router = DefaultRouter()

# Audio endpoints (nested under blog)
# These will be included from the main urls.py

# User preferences endpoints
router.register(r'preferences', UserAudioPreferenceViewSet, basename='audio-preferences')

# URL patterns for audio module
app_name = 'audio'

# These patterns will be included from blog_app/urls.py
# Blog-audio specific patterns (requires blog_pk)
audio_blog_patterns = [
    path('generate/', AudioViewSet.as_view({'post': 'generate'}), name='audio-generate'),
    path('status/', AudioViewSet.as_view({'get': 'status_check'}), name='audio-status'),
    path('', AudioViewSet.as_view({'get': 'get_audio'}), name='audio-detail'),
    path('questions/', AudioViewSet.as_view({'post': 'generate_questions'}), name='audio-questions'),
    path('reexplain/', AudioViewSet.as_view({'post': 'reexplain'}), name='audio-reexplain'),
    path('list/', AudioViewSet.as_view({'get': 'list_audio'}), name='audio-list'),
    path('<int:audio_id>/download/', AudioViewSet.as_view({'get': 'download'}), name='audio-download'),
]

urlpatterns = [
    # Audio preferences (user-specific)
    path('api/audio/', include(router.urls)),
]

