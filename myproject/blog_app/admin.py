from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Blog, Comment
from subscription.models import UserSubscription  # Required for the Inline view

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
    list_display = ('title', 'author', 'is_published', 'created_at')
    list_filter = ('is_published', 'author')
    search_fields = ('title', 'content')

admin.site.register(Comment)