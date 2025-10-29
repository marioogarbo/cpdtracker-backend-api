from rest_framework.permissions import BasePermission
from .models import Subscription

class IsSubscribed(BasePermission):
    """
    Allows access only to users with an active subscription.
    """
    message = "You must have an active subscription to access this feature."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            # Use select_related to optimize if you access user or plan details frequently from Subscription
            user_subscription = Subscription.objects.select_related('plan').get(user=request.user)
            return user_subscription.is_active
        except Subscription.DoesNotExist:
            return False
