from django.db import models
from django.conf import settings
from config.utils import CustomShortUUIDField
from django.utils import timezone

User = settings.AUTH_USER_MODEL

class SubscriptionPlan(models.Model):

    id = CustomShortUUIDField(primary_key=True, prefix='plan_', editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    features = models.JSONField(default=list, blank=True, help_text="Features included in the plan")
    custom_pricing = models.BooleanField(default=False, help_text="If True, pricing is negotiated/variable (e.g., Enterprise).")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class SubscriptionPrice(models.Model):
    INTERVAL_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    id = CustomShortUUIDField(primary_key=True, prefix='price_', editable=False)
    plan = models.ForeignKey(
        SubscriptionPlan, 
        on_delete=models.CASCADE, 
        related_name='pricing_tiers',
        help_text="Subscription plan this pricing tier belongs to")
    interval = models.CharField(
        max_length=10, 
        choices=INTERVAL_CHOICES, 
        default='monthly', 
        help_text="Billing interval for the pricing tier")
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        help_text="Price for the subscription tier")
    currency = models.CharField(
        max_length=3, 
        default='USD', 
        help_text="Currency code (e.g., USD, EUR)")
    stripe_price_id = models.CharField(
        max_length=100, 
        unique=True, 
        help_text="Stripe Price ID")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("plan", "interval")
        ordering = ["plan", "interval"]

    def __str__(self):
        return f"{self.plan.name} - {self.interval.capitalize()} - {self.price} {self.currency}"


class Subscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('past_due', 'Past Due'),
        ('trialing', 'Trialing'),
        ('unpaid', 'Unpaid'),
        ('incomplete', 'Incomplete'),
        ('incomplete_expired', 'Incomplete Expired'),
    ]

    id = CustomShortUUIDField(primary_key=True, prefix='sub_', editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription')
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True)
    price = models.ForeignKey(SubscriptionPrice, on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriptions')
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='incomplete')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.plan.name if self.plan else 'No Plan'} ({self.status})"

    @property
    def is_active(self):
        # Check if subscription is in an active status
        if self.status in ['active', 'trialing']:
            return True
        
        # For canceled subscriptions, check if still within the paid period
        if self.status == 'canceled' and self.end_date:
            return self.end_date > timezone.now()
        
        # For other statuses, check if there's a valid end_date in the future
        if self.end_date and self.end_date > timezone.now():
            return True
            
        return False
