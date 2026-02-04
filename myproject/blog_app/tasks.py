from celery import shared_task
from django.utils import timezone
from django.db.utils import ProgrammingError, OperationalError
from blog_app.models import Blog

# Import centralized MQTT publisher
from blog_app.mqtt_publisher import mqtt_publish


# ----------------------------------------------------
# TASK 1 — Publish a single scheduled blog (ETA task)
# ----------------------------------------------------
@shared_task
def publish_scheduled_blog(blog_id):
    try:
        blog = Blog.objects.get(id=blog_id)
        now = timezone.now()

        if blog.scheduled_publish_at and blog.scheduled_publish_at <= now:
            blog.is_published = True
            blog.published_at = blog.scheduled_publish_at
            blog.save()

            print(f"[publish_scheduled_blog] Blog {blog_id} published.")

            # Send MQTT Notification
            mqtt_publish("blog/published", {
                "blog_id": blog.id,
                "title": blog.title,
                "content": blog.content,
                "status": "published",
                "published_at": str(blog.published_at)
            })

        else:
            print(
                f"[publish_scheduled_blog] NOT published — now={now}, "
                f"scheduled={blog.scheduled_publish_at}"
            )

    except Blog.DoesNotExist:
        print(f"❌ Blog {blog_id} not found")


# ----------------------------------------------------
# TASK 2 — Periodic task to publish all due blogs
# ----------------------------------------------------
@shared_task
def publish_due_blogs():
    try:
        now = timezone.now()

        due = Blog.objects.filter(
            is_published=False,
            scheduled_publish_at__lte=now
        )

    except (ProgrammingError, OperationalError):
        print("⚠ Database not ready — skipping publish_due_blogs")
        return

    for blog in due:
        blog.is_published = True
        blog.published_at = blog.scheduled_publish_at
        blog.save()

        print(f"[publish_due_blogs] Published blog {blog.id}")

        # Send MQTT notification
        mqtt_publish("blog/published", {
            "blog_id": blog.id,
            "title": blog.title,
            "status": "published",
            "published_at": str(blog.published_at)
        })
