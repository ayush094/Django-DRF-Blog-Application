from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib import messages
from .models import User, Blog, Comment
from subscription.models import UserSubscription  # Required for the Inline view
from .ai_assistant import get_ai_response

# This allows you to see/edit a user's subscription directly on their profile page
class UserSubscriptionInline(admin.TabularInline):
    model = UserSubscription
    extra = 0  # No empty rows by default
    fields = ['plan', 'status', 'expires_at', 'created_at']
    readonly_fields = ['created_at']
    show_change_link = True

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Attach the subscription table to the bottom of the user edit page
    inlines = [UserSubscriptionInline]

    # 1. SETUP FOR EDITING EXISTING USERS
    fieldsets = UserAdmin.fieldsets + (
        ("Business Roles & Profile", {'fields': ('role', 'logo')}),
    )

    # 2. SETUP FOR CREATING NEW USERS (The + Add User screen)
    # This specifically adds the 'role' dropdown to the initial creation form
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Initial Role Assignment", {
            'classes': ('wide',),
            'fields': ('role',),
        }),
    )

    # 3. SETTING UP THE MAIN LIST VIEW
    list_display = (
        'id',
        'username', 
        'email', 
        'role', 
        'get_active_plan', 
        'is_staff', 
        'is_active'
    )
    
    # 4. QUICK ACTIONS
    list_editable = ('role',)  # Change roles directly from the table!
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('username', 'email')

    # Helper function to show the plan name in the user list
    def get_active_plan(self, obj):
        plan = obj.active_plan
        return f"⭐ {plan.name}" if plan else "❌ No Plan"
    
    get_active_plan.short_description = "Current Plan"

# Standard registration for Content
@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'is_published', 'ai_generated', 'created_at')
    list_filter = ('is_published', 'author', 'ai_generated')
    search_fields = ('title', 'content', 'ai_summary')
    readonly_fields = ('ai_summary', 'ai_improved_content', 'ai_generated', 'ai_generation_prompt', 'created_at', 'updated_at')
    fields = ('title', 'content', 'image', 'is_published', 'ai_summary', 'ai_improved_content', 'ai_generated', 'ai_generation_prompt', 'author')

    actions = ['improve_with_ai', 'generate_summary_with_ai', 'generate_blog_with_ai', 'expand_with_ai']

    def improve_with_ai(self, request, queryset):
        """AI-improve the content of selected blogs."""
        improved_count = 0
        for blog in queryset:
            try:
                improved_content = get_ai_response('improve', blog.content)
                blog.content = improved_content
                blog.save()
                improved_count += 1
            except Exception as e:
                messages.error(request, f"Failed to improve '{blog.title}': {str(e)}")

        if improved_count > 0:
            self.message_user(request, f"Successfully improved {improved_count} blog(s) with AI.")
    improve_with_ai.short_description = "🤖 Improve selected blogs with AI"

    def generate_summary_with_ai(self, request, queryset):
        """Generate AI summary for selected blogs."""
        summary_count = 0
        for blog in queryset:
            try:
                summary = get_ai_response('summarize', blog.content, blog.title)
                blog.ai_summary = summary
                blog.save()
                summary_count += 1
            except Exception as e:
                messages.error(request, f"Failed to generate summary for '{blog.title}': {str(e)}")

        if summary_count > 0:
            self.message_user(request, f"Successfully generated summaries for {summary_count} blog(s).")
    generate_summary_with_ai.short_description = "🤖 Generate AI summaries"

    def generate_blog_with_ai(self, request, queryset):
        """Generate new blog content from titles using AI."""
        if queryset.count() != 1:
            messages.warning(request, "Please select exactly one blog title to generate from.")
            return

        blog = queryset.first()
        try:
            generated_content = get_ai_response('generate', '', blog.title)
            blog.content = generated_content
            blog.ai_generated = True
            blog.ai_generation_prompt = f"Generate blog post based on title: {blog.title}"
            blog.save()
            messages.success(request, f"Successfully generated content for '{blog.title}'.")
        except Exception as e:
            messages.error(request, f"Failed to generate blog: {str(e)}")
    generate_blog_with_ai.short_description = "🤖 Generate blog content from title"

    def expand_with_ai(self, request, queryset):
        """Expand and elaborate on the content of selected blogs."""
        expanded_count = 0
        for blog in queryset:
            try:
                expanded_content = get_ai_response('expand', blog.content)
                blog.content = expanded_content
                blog.save()
                expanded_count += 1
            except Exception as e:
                messages.error(request, f"Failed to expand '{blog.title}': {str(e)}")

        if expanded_count > 0:
            self.message_user(request, f"Successfully expanded {expanded_count} blog(s) with AI.")
    expand_with_ai.short_description = "📝 Expand selected blogs with AI"

admin.site.register(Comment)