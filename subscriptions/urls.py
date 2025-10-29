from django.urls import path
from .views import (
    SubscriptionPlanListView,
    UserSubscriptionView,
    CreateCheckoutSessionView,
    CancelSubscriptionView,
    StripeWebhookView,
    VerifyCheckoutSessionView
)

urlpatterns = [
    path('plans/', SubscriptionPlanListView.as_view(), name='subscription-plans'),
    path('my-subscription/', UserSubscriptionView.as_view(), name='user-subscription'),
    path('create-checkout-session/', CreateCheckoutSessionView.as_view(), name='create-checkout-session'),
    path('cancel/', CancelSubscriptionView.as_view(), name='cancel-subscription'),
    path('verify-session/', VerifyCheckoutSessionView.as_view(), name='verify-session'),
    path('stripe-webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
]