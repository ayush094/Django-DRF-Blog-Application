from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Plan, UserSubscription
from .serializers import SubscribeSerializer, PlanListSerializer
from .services import create_razorpay_order, fetch_razorpay_payment
from .permissions import IsBusinessAdmin, IsAuthorUser

# 1. ADMIN MANAGEMENT
class PlanManagementViewSet(viewsets.ModelViewSet):
    """Business Admins use this to manage plans and features."""
    queryset = Plan.objects.all().prefetch_related('features')
    serializer_class = PlanListSerializer
    permission_classes = [IsBusinessAdmin]

    @swagger_auto_schema(operation_summary="Create Plan with Features")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

# 2. USER DASHBOARD (The Grandfathering Check)
class UserSubscriptionStatusAPIView(APIView):
    """
    Returns the specific features the user 'locked in' at purchase time.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Look for the current ACTIVE and non-expired subscription
        sub = request.user.subscriptions.filter(
            status="ACTIVE", 
            expires_at__gt=timezone.now()
        ).select_related('plan').first()

        if not sub:
            return Response({"active": False, "message": "No active subscription"})

        active_codes = sub.plan.features.values_list('code', flat=True)

        # Calculate dynamic limit
        base_limit = sub.plan.blog_limit
        total_limit = base_limit + 2 if "plus_2_blogs" in active_codes else base_limit
        # Fetches the 7 features (hd_images, seo_tools, etc.) tied to the user's plan version
        features = sub.plan.features.values('name', 'code')
        
        return Response({
            "active": True,
            "plan_name": sub.plan.name,
            "expires_at": sub.expires_at,
            "unlocked_features": list(features),
            "usage": {
                "blogs_posted": request.user.blogs.count(),
                "limit": sub.plan.blog_limit
            },
            "blogs_remaining": "Unlimited" if sub.plan.features.filter(code="unlimited_blogs").exists() 
                               else max(0, sub.plan.blog_limit - request.user.blogs.count())
        })

# 3. PUBLIC VIEW
class PlanListAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(responses={200: PlanListSerializer(many=True)})
    def get(self, request):
        plans = Plan.objects.filter(is_active=True).prefetch_related('features')
        serializer = PlanListSerializer(plans, many=True)
        return Response(serializer.data)

# 4. PURCHASE & VERIFY
class SubscribeAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAuthorUser]

    @swagger_auto_schema(request_body=SubscribeSerializer)
    def post(self, request):
        # Check for existing active plan
        if request.user.subscriptions.filter(status="ACTIVE", expires_at__gt=timezone.now()).exists():
            return Response({"detail": "You already have an active plan."}, status=400)
        
        serializer = SubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan = Plan.objects.get(id=serializer.validated_data["plan_id"])
        order = create_razorpay_order(plan.price)

        UserSubscription.objects.create(
            user=request.user, plan=plan, 
            razorpay_order_id=order["id"], status="PENDING",
            grandfathered_snapshot={}
        )

        return Response({
            "order_id": order["id"], "amount": plan.price, "key": settings.RAZORPAY_KEY_ID
        }, status=201)

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class VerifyPaymentAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAuthorUser]

    @swagger_auto_schema(
        operation_summary="Verify Payment and Activate Plan",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["razorpay_order_id", "razorpay_payment_id"],
            properties={
                "razorpay_order_id": openapi.Schema(type=openapi.TYPE_STRING, description="Order ID from Razorpay"),
                "razorpay_payment_id": openapi.Schema(type=openapi.TYPE_STRING, description="Payment ID from Razorpay"),
            },
        ),
        responses={200: "Plan Activated", 400: "Payment Failed", 404: "Order Not Found"}
    )
    def post(self, request):
        # 1. Get data from the Request Body
        order_id = request.data.get("razorpay_order_id")
        payment_id = request.data.get("razorpay_payment_id")

        # 2. Basic Validation: Ensure fields are not empty
        if not order_id or not payment_id:
            return Response(
                {"detail": "Both razorpay_order_id and razorpay_payment_id are required in the body."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Find the subscription record
        sub = UserSubscription.objects.filter(
            user=request.user, 
            razorpay_order_id=order_id
        ).first()

        if not sub: 
            return Response({"detail": f"Order {order_id} not found for this user."}, status=404)

        # 4. Fetch status from Razorpay (using your service)
        try:
            payment = fetch_razorpay_payment(payment_id)
        except Exception as e:
            return Response({"detail": f"Razorpay error: {str(e)}"}, status=400)

        # 5. Activate if payment is successful
        if payment["status"] == "captured":
            sub.status = "ACTIVE"

            sub.grandfathered_snapshot = {
                "codes": list(sub.plan.features.values_list('code', flat=True)),
                "blog_limit": sub.plan.blog_limit,
                "captured_at": str(timezone.now())
            }

            sub.razorpay_payment_id = payment["id"]

            
            # Set expiry based on billing cycle
            days = 28 if sub.plan.billing_cycle == "monthly" else 365
            sub.expires_at = timezone.now() + timedelta(days=days)
            sub.save()

            return Response({
                "detail": "Activated",
                "features": list(sub.plan.features.values_list('code', flat=True))
            }, status=200)

        return Response({"detail": "Payment failed or not captured"}, status=400)