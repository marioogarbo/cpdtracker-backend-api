from django.contrib import admin
from .models import SubscriptionPlan, Subscription, SubscriptionPrice


class SubscriptionPriceInline(admin.TabularInline):
    model = SubscriptionPrice
    extra = 1
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'custom_pricing', 'created_at']
    list_filter = ['is_active', 'custom_pricing']
    search_fields = ['name', 'description']
    ordering = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [SubscriptionPriceInline]


@admin.register(Subscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'plan', 'price', 'status', 'start_date', 'end_date', 
        'is_active', 'created_at'
    ]
    list_filter = ['status', 'plan', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = [
        'id', 'stripe_customer_id', 'stripe_subscription_id', 
        'created_at', 'updated_at'
    ]
    raw_id_fields = ['user', 'plan', 'price']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'plan', 'price')
