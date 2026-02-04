from rest_framework import serializers
from .models import Plan, PlanFeature

class PlanFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanFeature
        fields = ["name", "code"]
        extra_kwargs = {
            "code": {"validators": []},  # Allows reusing existing codes in nested creation
        }

class PlanListSerializer(serializers.ModelSerializer):
    # Removed read_only=True so it shows in Swagger POST body
    features = PlanFeatureSerializer(many=True, required=False)

    class Meta:
        model = Plan
        fields = ["id", "name", "price", "billing_cycle", "blog_limit", "image_limit", "features"]

    def create(self, validated_data):
        # Extract features from validated_data (Professional DRF way)
        features_data = validated_data.pop('features', [])
        plan = Plan.objects.create(**validated_data)
        
        for f_data in features_data:
            # Connect existing codes or create new ones
            feature_obj, _ = PlanFeature.objects.get_or_create(
                code=f_data['code'], 
                defaults={'name': f_data['name']}
            )
            plan.features.add(feature_obj)
        
        return plan

class SubscribeSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()

    def validate_plan_id(self, value):
        if not Plan.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Invalid or inactive plan")
        return value