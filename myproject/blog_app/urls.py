
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import AuthViewSet, BlogViewSet, CommentViewSet

router = DefaultRouter()
router.register("auth", AuthViewSet, basename="auth")
router.register("blogs", BlogViewSet, basename="blogs")
router.register("comments", CommentViewSet, basename="comments")

urlpatterns = [
    path("", include(router.urls)),
]
