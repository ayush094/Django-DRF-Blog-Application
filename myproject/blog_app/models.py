from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone
# from datetime import timedelta

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Business Admin'),
        ('author', 'Author'),
        ('user', 'Normal User'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    logo = models.ImageField(upload_to="author_logos/", null=True, blank=True)
    
    @property
    def active_plan(self):
        subscription = self.subscriptions.filter(
            status="ACTIVE",
            expires_at__gt=timezone.now()
        ).select_related("plan").first()

        return subscription.plan if subscription else None

    def __str__(self):
        return f"{self.username} - {self.role}"


class Blog(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to="blog_images/", null=True, blank=True)
    
    # --- Feature: password_blog ---
    is_password_protected = models.BooleanField(default=False)
    password = models.CharField(max_length=128, null=True, blank=True)
    
    # --- Feature: seo_tools ---
    meta_title = models.CharField(max_length=255, null=True, blank=True)
    
    # --- Feature: custom_themes ---
    # theme_id = models.CharField(max_length=50, null=True, blank=True)
    
    # Existing fields
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blogs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False)
    scheduled_publish_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title


class Comment(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='comments')
    commenter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.commenter.username} on {self.blog.title}"


class Like(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blog', 'user')

    def __str__(self):
        return f"{self.user.username} likes {self.blog.title}"
