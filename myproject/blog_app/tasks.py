import logging
import logging.config
from django.conf import settings
from celery import shared_task
from django.utils import timezone
from django.db.utils import ProgrammingError, OperationalError
from blog_app.models import Blog
from blog_app.mqtt_publisher import mqtt_publish


# ----------------------------------------------------
# FORCE DJANGO LOGGING INTO CELERY
# ----------------------------------------------------
logging.config.dictConfig(settings.LOGGING)

logger = logging.getLogger("blog_publisher")


# ----------------------------------------------------
# TASK 1 — Publish Single Scheduled Blog
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

            logger.info(
                "Blog published",
                extra={
                    "event": "blog_published",
                    "blog_id": blog.id,
                    "title": blog.title,
                    "status": "published",
                    "published_at": str(blog.published_at),
                }
            )

            mqtt_publish("blog/published", {
                "blog_id": blog.id,
                "title": blog.title,
                "status": "published",
                "published_at": str(blog.published_at),
            })

        else:
            logger.info(
                "Blog not published yet",
                extra={
                    "event": "blog_not_published",
                    "blog_id": blog.id,
                    "scheduled_at": str(blog.scheduled_publish_at),
                    "current_time": str(now),
                }
            )

    except Blog.DoesNotExist:
        logger.error(
            "Blog not found",
            extra={
                "event": "blog_not_found",
                "blog_id": blog_id,
            }
        )


# ----------------------------------------------------
# TASK 2 — Publish All Due Blogs
# ----------------------------------------------------
@shared_task
def publish_due_blogs():
    try:
        now = timezone.now()

        due_blogs = Blog.objects.filter(
            is_published=False,
            scheduled_publish_at__lte=now,
        )

    except (ProgrammingError, OperationalError):
        logger.warning(
            "Database not ready",
            extra={
                "event": "database_not_ready",
                "task": "publish_due_blogs",
            }
        )
        return

    for blog in due_blogs:
        blog.is_published = True
        blog.published_at = blog.scheduled_publish_at
        blog.save()

        logger.info(
            "Blog published",
            extra={
                "event": "blog_published",
                "blog_id": blog.id,
                "title": blog.title,
                "status": "published",
                "published_at": str(blog.published_at),
            }
        )

        mqtt_publish("blog/published", {
            "blog_id": blog.id,
            "title": blog.title,
            "status": "published",
            "published_at": str(blog.published_at),
        })
