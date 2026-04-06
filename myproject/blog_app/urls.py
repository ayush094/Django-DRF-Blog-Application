
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import AIAssistViewSet, AuthViewSet, BlogViewSet, CommentViewSet, AudioHubView
from blog_app.audio import urls as audio_urls

router = DefaultRouter()
router.register("auth", AuthViewSet, basename="auth")
router.register("blogs", BlogViewSet, basename="blogs")
router.register("comments", CommentViewSet, basename="comments")
router.register("ai", AIAssistViewSet, basename="ai")

urlpatterns = [
    # Audio UI Frontend
    path('audio-hub/', AudioHubView.as_view(), name='audio-hub'),

    # Audio API endpoints (must come before router to avoid conflicts)
    path('blogs/<int:blog_pk>/audio/', include(audio_urls.audio_blog_patterns)),
    path('audio/', include(audio_urls.urlpatterns)),

    # Router endpoints
    path("", include(router.urls)),
]
