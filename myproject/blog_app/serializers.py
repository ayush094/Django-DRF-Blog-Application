from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import Blog, Comment, Like
import pytz
from PIL import Image
from django.utils import timezone

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role' , 'logo']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'password2', 'email', 'role' , 'logo']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class CommentSerializer(serializers.ModelSerializer):
    commenter = UserSerializer(read_only=True)
    blog = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "blog", "commenter", "content", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at", "commenter", "blog"]


class BlogCreateSerializer(serializers.ModelSerializer):
    # Ensure these fields exist in your Blog model
    class Meta:
        model = Blog
        fields = [
            'title', 'content', 'image', 'scheduled_publish_at', 
            'is_password_protected', 'password', 'meta_title',
        ]

    def validate(self, data):
        user = self.context['request'].user
        
        # 1. Try to find an active subscription
        sub = user.subscriptions.filter(
            status="ACTIVE", 
            expires_at__gt=timezone.now()
        ).first()

        # 2. Determine Permissions (Paid vs. Free)
        if sub:
            snapshot = getattr(sub , "grandfathered_snapshot" , {})

            if snapshot and "codes" in snapshot:
                active_codes = snapshot.get("codes", [])
                allowed_limit = snapshot.get("blog_limit", 1)
            else:
                plan = sub.plan
                active_codes = list(plan.features.values_list('code', flat=True))
                allowed_limit = plan.blog_limit
            
            # Apply the +2 bonus if they have the specific code
            if "plus_2_blogs" in active_codes:
                allowed_limit += 2
        else:
            # User has NO active plan: Fallback to "Free Tier" defaults
            active_codes = []  # No premium features (No passwords, No SEO)
            allowed_limit = 1   # Set this to your desired free limit (e.g., 1 or 2)

        # 3. Check: Blog Post Limit
        # Skip check if user has 'unlimited_blogs' code
        if "unlimited_blogs" not in active_codes:
            if user.blogs.count() >= allowed_limit:
                raise serializers.ValidationError(
                    f"Limit reached. Free users can post up to {allowed_limit} blog(s). "
                    "Please upgrade your plan for more."
                )

        # 3. CHECK: HD Images (hd_images)
        image = data.get('image')
        if image and "hd_images" not in active_codes:
            img = Image.open(image)
            # Standard production check: block if resolution > 1280px (720p/HD boundary)
            if img.width > 1280 or img.height > 1280:
                raise serializers.ValidationError("HD images are restricted to premium plans.")

        # 4. CHECK: Password Protection (password_blog)
        if data.get('is_password_protected') and "password_blog" not in active_codes:
            raise serializers.ValidationError("Password protecting blogs is a premium feature.")

        # 5. CHECK: SEO Tools (seo_tools)
        if data.get('meta_title') and "seo_tools" not in active_codes:
            raise serializers.ValidationError("SEO meta-tools are not included in your current plan.")

        # 6. CHECK: Custom Themes (custom_themes)
        # if data.get('theme_id') and "custom_themes" not in active_codes:
        #     raise serializers.ValidationError("Custom themes require a professional tier subscription.")
        return data

class BlogSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    comment_count = serializers.IntegerField(source='comments.count', read_only=True)
    comments = CommentSerializer(
        many=True,
        source="comment_set",
        read_only=True
    )
    like_count = serializers.IntegerField(source='likes.count', read_only=True)
    liked = serializers.SerializerMethodField()
    is_published = serializers.BooleanField(read_only=True)
    scheduled_publish_at_IST = serializers.SerializerMethodField()
    published_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Blog
        fields = '__all__'

    def get_scheduled_publish_at_IST(self, obj):
        if obj.scheduled_publish_at:
            ist = pytz.timezone("Asia/Kolkata")
            return obj.scheduled_publish_at.astimezone(ist)
        return None

    def get_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False
