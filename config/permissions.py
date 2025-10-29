from rest_framework.permissions import BasePermission
from subscriptions.models import Subscription


class IsSubscribed(BasePermission):
    """
    Custom permission to check if the user has an active subscription.
    """
    message = "You must have an active subscription to access this feature."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            # Check subscription status
            user_subscription = Subscription.objects.select_related('plan').get(user=request.user)
            return user_subscription.is_active
        except Subscription.DoesNotExist:
            return False


class IsProfessional(BasePermission):
    """
    Custom permission to only allow users with 'professional' role.
    """
    message = "You don't have permission to access this resource."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return hasattr(request.user, 'role') and request.user.role == 'professional'


class IsProfessionalSubscriber(BasePermission):
    """
    Combined permission that checks if user is authenticated, has professional role,
    and has an active subscription.
    """
    message = "Access denied. You don't have the required permissions."
    
    def has_permission(self, request, view):
        # Check authentication
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check professional role
        if not hasattr(request.user, 'role') or request.user.role != 'professional':
            return False
        
        # Check subscription status
        try:
            user_subscription = Subscription.objects.select_related('plan').get(user=request.user)
            return user_subscription.is_active
        except Subscription.DoesNotExist:
            return False