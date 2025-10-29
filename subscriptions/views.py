import stripe
import logging
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import SubscriptionPlan, Subscription, SubscriptionPrice
from .serializers import (
    SubscriptionPlanSerializer, 
    UserSubscriptionSerializer,
    CreateCheckoutSessionSerializer
)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)

class SubscriptionPlanListView(generics.ListAPIView):
    """List all active subscription plans"""
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.AllowAny]

    @method_decorator(cache_page(60 * 15, key_prefix='subscription_plans'))
    def dispatch(self, *args, **kwargs):
        # Cache the plan list for 15 minutes for all users
        return super().dispatch(*args, **kwargs)


class UserSubscriptionView(generics.RetrieveAPIView):
    """Get current user's subscription details"""
    serializer_class = UserSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(cache_page(60 * 15, key_prefix='user_subscription'))
    def dispatch(self, *args, **kwargs):
        # Cache the plan list for 15 minutes for all users
        return super().dispatch(*args, **kwargs)

    def get_object(self):
        subscription, created = Subscription.objects.get_or_create(
            user=self.request.user,
            defaults={'status': 'incomplete'}
        )
        return subscription


class CreateCheckoutSessionView(APIView):
    """Create a Stripe checkout session for subscription"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CreateCheckoutSessionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            price_id = serializer.validated_data['price_id']
            price = SubscriptionPrice.objects.select_related('plan').get(id=price_id)
            plan = price.plan
            
            if not plan.is_active:
                return Response(
                    {'error': 'This subscription plan is not currently available'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get or create user subscription
            user_subscription, created = Subscription.objects.get_or_create(
                user=request.user,
                defaults={'status': 'incomplete'}
            )

            # Create or get Stripe customer
            if user_subscription.stripe_customer_id:
                customer_id = user_subscription.stripe_customer_id
            else:
                customer = stripe.Customer.create(
                    email=request.user.email,
                    name=f"{request.user.first_name} {request.user.last_name}",
                    metadata={
                        'user_id': str(request.user.id),
                        'subscription_id': str(user_subscription.id)
                    }
                )
                customer_id = customer.id
                user_subscription.stripe_customer_id = customer_id
                user_subscription.save()

            # Create checkout session
            checkout_session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price.stripe_price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=serializer.validated_data.get(
                    'success_url', 
                    settings.STRIPE_SUCCESS_URL
                ),
                cancel_url=serializer.validated_data.get(
                    'cancel_url', 
                    settings.STRIPE_CANCEL_URL
                ),
                metadata={
                    'user_id': str(request.user.id),
                    'subscription_id': str(user_subscription.id),
                    'plan_id': str(plan.id),
                    'price_id': str(price.id)
                }
            )

            return Response({
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id
            })

        except SubscriptionPlan.DoesNotExist:
            return Response(
                {'error': 'Invalid subscription plan'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {str(e)}")
            return Response(
                {'error': 'Payment processing error'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error in checkout: {str(e)}")
            return Response(
                {'error': 'An unexpected error occurred'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CancelSubscriptionView(APIView):
    """Cancel user's active subscription"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            user_subscription = Subscription.objects.get(user=request.user)
            
            if not user_subscription.stripe_subscription_id:
                return Response(
                    {'error': 'No active subscription found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            # Cancel subscription in Stripe
            stripe.Subscription.modify(
                user_subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )

            return Response({
                'message': 'Subscription will be canceled at the end of the current billing period'
            })

        except Subscription.DoesNotExist:
            return Response(
                {'error': 'No subscription found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {str(e)}")
            return Response(
                {'error': 'Failed to cancel subscription'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error in cancellation: {str(e)}")
            return Response(
                {'error': 'An unexpected error occurred'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    """Handle Stripe webhooks"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError:
            logger.error("Invalid payload in webhook")
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid signature in webhook")
            return HttpResponse(status=400)

        # Handle the event
        if event['type'] == 'checkout.session.completed':
            self.handle_checkout_session_completed(event['data']['object'])
        elif event['type'] == 'customer.subscription.updated':
            self.handle_subscription_updated(event['data']['object'])
        elif event['type'] == 'customer.subscription.deleted':
            self.handle_subscription_deleted(event['data']['object'])
        elif event['type'] == 'invoice.payment_succeeded':
            self.handle_payment_succeeded(event['data']['object'])
        elif event['type'] == 'invoice.payment_failed':
            self.handle_payment_failed(event['data']['object'])
        else:
            logger.info(f"Unhandled event type: {event['type']}")

        return HttpResponse(status=200)

    def handle_checkout_session_completed(self, session):
        """Handle successful checkout session"""
        try:
            user_id = session['metadata'].get('user_id')
            subscription_id = session['metadata'].get('subscription_id')
            plan_id = session['metadata'].get('plan_id')
            price_id = session['metadata'].get('price_id')

            if not all([user_id, subscription_id, plan_id]):
                logger.error("Missing metadata in checkout session")
                return

            user_subscription = Subscription.objects.get(id=subscription_id)
            plan = SubscriptionPlan.objects.get(id=plan_id)
            
            # Get price if available
            price = None
            if price_id:
                try:
                    price = SubscriptionPrice.objects.get(id=price_id)
                except SubscriptionPrice.DoesNotExist:
                    logger.warning(f"Price with ID {price_id} not found")

            # Get the subscription from Stripe
            stripe_subscription = stripe.Subscription.retrieve(session['subscription'])
            logger.info(f"Stripe subscription object: {stripe_subscription}")

            # Safely get current_period_end
            current_period_end_ts = stripe_subscription.get('current_period_end')
            if not current_period_end_ts:
                logger.error(f"Stripe subscription missing 'current_period_end': {stripe_subscription}")
                current_period_end = None
            else:
                from datetime import datetime
                current_period_end = datetime.fromtimestamp(current_period_end_ts)

            # Update user subscription
            user_subscription.plan = plan
            if price:
                user_subscription.price = price
            user_subscription.stripe_subscription_id = session['subscription']
            user_subscription.status = stripe_subscription['status']
            if current_period_end:
                user_subscription.end_date = current_period_end  # Set the end date to current period end
            user_subscription.save()

            logger.info(f"Subscription activated for user {user_id}")

        except Exception as e:
            logger.error(f"Error handling checkout session completed: {str(e)}")

    def handle_subscription_updated(self, subscription):
        """Handle subscription updates"""
        try:
            user_subscription = Subscription.objects.get(
                stripe_subscription_id=subscription['id']
            )
            user_subscription.status = subscription['status']
            
            # Always update the end date to the current period end
            from datetime import datetime
            user_subscription.end_date = datetime.fromtimestamp(
                subscription['current_period_end']
            )
            
            # Additional metadata when subscription is being canceled
            if subscription['cancel_at_period_end'] and not user_subscription.canceled_at:
                user_subscription.canceled_at = timezone.now()
            
            user_subscription.save()
            logger.info(f"Subscription updated: {subscription['id']}")

        except Subscription.DoesNotExist:
            logger.error(f"UserSubscription not found for Stripe subscription: {subscription['id']}")
        except Exception as e:
            logger.error(f"Error handling subscription updated: {str(e)}")

    def handle_subscription_deleted(self, subscription):
        """Handle subscription deletion"""
        try:
            user_subscription = Subscription.objects.get(
                stripe_subscription_id=subscription['id']
            )
            user_subscription.status = 'canceled'
            user_subscription.canceled_at = timezone.now()
            user_subscription.save()

            logger.info(f"Subscription canceled: {subscription['id']}")

        except Subscription.DoesNotExist:
            logger.error(f"UserSubscription not found for Stripe subscription: {subscription['id']}")
        except Exception as e:
            logger.error(f"Error handling subscription deleted: {str(e)}")

    def handle_payment_succeeded(self, invoice):
        """Handle successful payment"""
        try:
            subscription_id = invoice['subscription']
            if subscription_id:
                user_subscription = Subscription.objects.get(
                    stripe_subscription_id=subscription_id
                )
                
                # Update status if needed
                if user_subscription.status != 'active':
                    user_subscription.status = 'active'
                
                # Update end date with new billing period end
                stripe_subscription = stripe.Subscription.retrieve(subscription_id)
                from datetime import datetime
                current_period_end = datetime.fromtimestamp(stripe_subscription['current_period_end'])
                user_subscription.end_date = current_period_end
                
                user_subscription.save()

            logger.info(f"Payment succeeded for subscription: {subscription_id}")

        except Subscription.DoesNotExist:
            logger.error(f"UserSubscription not found for invoice: {invoice['id']}")
        except Exception as e:
            logger.error(f"Error handling payment succeeded: {str(e)}")

    def handle_payment_failed(self, invoice):
        """Handle failed payment"""
        try:
            subscription_id = invoice['subscription']
            if subscription_id:
                user_subscription = Subscription.objects.get(
                    stripe_subscription_id=subscription_id
                )
                user_subscription.status = 'past_due'
                user_subscription.save()

            logger.info(f"Payment failed for subscription: {subscription_id}")

        except Subscription.DoesNotExist:
            logger.error(f"UserSubscription not found for invoice: {invoice['id']}")
        except Exception as e:
            logger.error(f"Error handling payment failed: {str(e)}")


class VerifyCheckoutSessionView(APIView):
    """Verify Stripe checkout session and return status"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        session_id = request.query_params.get('session_id')
        
        if not session_id:
            return Response(
                {'error': 'Session ID is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Retrieve session from Stripe
            session = stripe.checkout.Session.retrieve(session_id)
            
            # Verify the session belongs to the current user
            user_id = session.metadata.get('user_id')
            if str(request.user.id) != user_id:
                return Response(
                    {'error': 'Unauthorized access to session'}, 
                    status=status.HTTP_403_FORBIDDEN
                )

            # Get subscription details if session is completed
            subscription_data = None
            if session.status == 'complete' and session.subscription:
                try:
                    user_subscription = Subscription.objects.select_related('plan', 'price').get(
                        user=request.user,
                        stripe_subscription_id=session.subscription
                    )
                    subscription_data = UserSubscriptionSerializer(user_subscription).data
                except Subscription.DoesNotExist:
                    pass

            return Response({
                'session_id': session.id,
                'status': session.status,
                'customer_email': session.customer_details.get('email') if session.customer_details else None,
                'amount_total': session.amount_total,
                'currency': session.currency,
                'subscription': subscription_data,
                'payment_status': session.payment_status,
            })

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error during session verification: {str(e)}")
            return Response(
                {'error': 'Failed to verify session'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error during session verification: {str(e)}")
            return Response(
                {'error': 'An unexpected error occurred'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
