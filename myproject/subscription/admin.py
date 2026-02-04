from django.contrib import admin
from django.utils import timezone
from .models import Plan, PlanFeature, UserSubscription

@admin.register(PlanFeature)
class PlanFeatureAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "billing_cycle", "is_active")
    list_editable = ("is_active",)
    filter_horizontal = ("features",)

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "expires_at", "is_valid")
    list_filter = ("status", "plan")
    search_fields = ("user__username", "razorpay_order_id")
    
    # We make the snapshot READ-ONLY so Admin can see it but not break it
    readonly_fields = ("created_at", "grandfathered_snapshot")
    
    # Organizes the detail view into sections
    fieldsets = (
        ("User Info", {"fields": ("user", "plan", "status")}),
        ("Payment Details", {"fields": ("razorpay_order_id", "razorpay_payment_id")}),
        ("Dates", {"fields": ("created_at", "expires_at")}),
        ("Grandfathering Data", {
            "fields": ("grandfathered_snapshot",),
            "description": "Locked features captured at time of payment."
        }),
    )

    @admin.display(boolean=True, description="Currently Valid")
    def is_valid(self, obj):
        if obj.status == "ACTIVE" and obj.expires_at:
            return obj.expires_at > timezone.now()
        return False