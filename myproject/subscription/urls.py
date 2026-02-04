from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PlanManagementViewSet, 
    PlanListAPIView, 
    SubscribeAPIView, 
    VerifyPaymentAPIView,
    UserSubscriptionStatusAPIView  # New Dashboard View
)

router = DefaultRouter()
router.register(r'manage-plans', PlanManagementViewSet, basename='manage-plans')

urlpatterns = [
    path('', include(router.urls)), 
    path('status/', UserSubscriptionStatusAPIView.as_view(), name='sub-status'), # Added for Dashboard
    path('list-plans/', PlanListAPIView.as_view(), name='plan-list'),
    path('subscribe/', SubscribeAPIView.as_view(), name='subscribe'),
    path('verify-payment/', VerifyPaymentAPIView.as_view(), name='verify-payment'),
]