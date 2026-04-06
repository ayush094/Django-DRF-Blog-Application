# Generated manually for blog_app.audio initial migration
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('blog_app', '0001_initial'),  # Depends on Blog and User models
    ]

    operations = [
        migrations.CreateModel(
            name='AudioFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mode', models.CharField(choices=[('conversation', 'Conversation (Podcast Style)'), ('explain', 'Explain (Teacher Style)'), ('summary', 'Summary (Quick Overview)')], default='explain', max_length=20)),
                ('language', models.CharField(choices=[('en', 'English'), ('hi', 'Hindi (हिंदी)'), ('gu', 'Gujarati (ગુજરાતી)')], default='en', max_length=5)),
                ('understanding_level', models.CharField(choices=[('beginner', 'Beginner - Simple explanations with analogies'), ('intermediate', 'Intermediate - Balanced depth and accessibility'), ('expert', 'Expert - Technical terms, focused insights')], default='intermediate', max_length=15)),
                ('mood', models.CharField(choices=[('serious', 'Serious - Professional tone'), ('storytelling', 'Storytelling - Narrative with dramatic elements'), ('educational', 'Educational - Clear, structured delivery')], default='educational', max_length=20)),
                ('audio_file', models.FileField(blank=True, null=True, upload_to='blog_app.audio.models.audio_file_path')),
                ('status', models.CharField(choices=[('pending', 'Pending - Audio generation in queue'), ('processing', 'Processing - Audio being generated'), ('ready', 'Ready - Audio available for playback'), ('failed', 'Failed - Audio generation error')], default='pending', max_length=20)),
                ('duration_seconds', models.IntegerField(default=0)),
                ('sections', models.JSONField(default=dict)),
                ('transcript', models.TextField(default='')),
                ('summary', models.TextField(default='')),
                ('suggestions', models.JSONField(default=list)),
                ('questions', models.JSONField(default=list)),
                ('error_message', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('download_count', models.IntegerField(default=0)),
                ('blog', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audio_files', to='blog_app.blog')),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['blog', 'mode', 'language'], name='audio_blog_mode_lang_idx'), models.Index(fields=['status', 'created_at'], name='audio_status_created_idx')],
                'unique_together': {('blog', 'mode', 'language', 'understanding_level', 'mood')},
            },
        ),
        migrations.CreateModel(
            name='UserAudioPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('default_mode', models.CharField(choices=[('conversation', 'Conversation (Podcast Style)'), ('explain', 'Explain (Teacher Style)'), ('summary', 'Summary (Quick Overview)')], default='explain', max_length=20)),
                ('default_language', models.CharField(choices=[('en', 'English'), ('hi', 'Hindi (हिंदी)'), ('gu', 'Gujarati (ગુજરાતી)')], default='en', max_length=5)),
                ('default_understanding_level', models.CharField(choices=[('beginner', 'Beginner - Simple explanations with analogies'), ('intermediate', 'Intermediate - Balanced depth and accessibility'), ('expert', 'Expert - Technical terms, focused insights')], default='intermediate', max_length=15)),
                ('default_mood', models.CharField(choices=[('serious', 'Serious - Professional tone'), ('storytelling', 'Storytelling - Narrative with dramatic elements'), ('educational', 'Educational - Clear, structured delivery')], default='educational', max_length=20)),
                ('default_speed', models.FloatField(default=1.0)),
                ('default_volume', models.FloatField(default=0.8)),
                ('autoplay', models.BooleanField(default=False)),
                ('highlight_sync_enabled', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='audio_preferences', to='blog_app.user')),
            ],
            options={
                'verbose_name': 'User Audio Preference',
                'verbose_name_plural': 'User Audio Preferences',
            },
        ),
        migrations.CreateModel(
            name='AudioBookmark',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp_seconds', models.IntegerField()),
                ('title', models.CharField(blank=True, max_length=100)),
                ('note', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('audio_file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bookmarks', to='audio.AudioFile')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audio_bookmarks', to='blog_app.user')),
            ],
            options={
                'ordering': ['timestamp_seconds'],
                'indexes': [models.Index(fields=['user', 'audio_file'], name='bookmark_user_audio_idx')],
            },
        ),
        migrations.CreateModel(
            name='AudioQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question_type', models.CharField(choices=[('recall', 'Recall - Tests memory of key facts'), ('understand', 'Understand - Tests comprehension'), ('apply', 'Apply - Tests application of concepts'), ('analyze', 'Analyze - Tests critical thinking')], default='understand', max_length=20)),
                ('question', models.TextField()),
                ('options', models.JSONField(default=list)),
                ('correct_answer', models.CharField(max_length=500)),
                ('explanation', models.TextField(blank=True)),
                ('order', models.IntegerField(default=0)),
                ('audio_file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audio_questions', to='audio.AudioFile')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
    ]
