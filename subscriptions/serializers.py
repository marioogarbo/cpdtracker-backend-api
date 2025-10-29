from rest_framework import serializers
from .models import SubscriptionPlan, Subscription, SubscriptionPrice


class SubscriptionPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPrice
        fields = [
            'id', 'interval', 'price', 'currency',
        ]
        read_only_fields = ['id']


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    pricing_tiers = SubscriptionPriceSerializer(many=True, read_only=True)
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'description', 'features', 'custom_pricing',
            'pricing_tiers'
        ]
        read_only_fields = ['id', 'created_at']


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    price = SubscriptionPriceSerializer(read_only=True)
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'plan', 'price', 'status', 'start_date', 'end_date', 
            'trial_end', 'canceled_at', 'is_active'
        ]
        read_only_fields = [
            'id', 'status', 'start_date', 'end_date', 'trial_end', 
            'canceled_at', 'created_at'
        ]


class CreateCheckoutSessionSerializer(serializers.Serializer):
    price_id = serializers.CharField(max_length=100)
    success_url = serializers.URLField(required=False)
    cancel_url = serializers.URLField(required=False)


class StripeWebhookSerializer(serializers.Serializer):
    """Serializer for Stripe webhook data validation"""
    pass