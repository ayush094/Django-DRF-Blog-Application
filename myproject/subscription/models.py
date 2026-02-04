from django.db import models
from django.conf import settings
from django.utils import timezone

class PlanFeature(models.Model):

    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=50, unique=True, help_text="Used in code (e.g., 'fast_support')")

    def __str__(self):
        return self.name

class Plan(models.Model):
    BILLING_CYCLE_CHOICES = (
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    )

    name = models.CharField(max_length=100)
    price = models.PositiveIntegerField(help_text="Price in INR")
    billing_cycle = models.CharField(max_length=10, choices=BILLING_CYCLE_CHOICES)
    
    # Keep these for numeric limits
    blog_limit = models.PositiveIntegerField(help_text="Number of blogs allowed per cycle")
    image_limit = models.PositiveIntegerField(help_text="Number of images allowed per cycle")
    
    # NEW: Many-to-Many relationship for dynamic features
    features = models.ManyToManyField(PlanFeature, blank=True, related_name="plans")

    is_active = models.BooleanField(default=True)
    razorpay_plan_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.billing_cycle}) - ₹{self.price}"

# [UserSubscription remains exactly as you wrote it]
class UserSubscription(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("ACTIVE", "Active"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
        ("EXPIRED", "Expired"),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    razorpay_order_id = models.CharField(max_length=100)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    grandfathered_snapshot = models.JSONField(null=True, blank=True, help_text="Snapshot of plan features and limits at time of subscription")

    @property
    def is_expired(self):
        return self.expires_at and self.expires_at < timezone.now()

    def __str__(self):
        return f"{self.user} - {self.plan.name} - {self.status}"