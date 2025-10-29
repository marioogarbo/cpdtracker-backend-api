from django.urls import path
from .views import (
    ApprovedCPDActivitiesListView,
    CPDActivityDetailView,
    CreateManualCPDActivityView,
    UserManualCPDActivitiesView,
    ProviderCPDActivitiesListView,
    CreateProviderCPDActivityView,
    EnhancedCPDActivitiesListView,
    cpd_activity_categories,
    cpd_activity_search_suggestions,
    provider_stats,
    ProviderCPDActivityDestroyView,
    ListRecordedWebinarsView
)

urlpatterns = [
    path('', ApprovedCPDActivitiesListView.as_view(), name='cpd-activities-list'),
    path('enhanced/', EnhancedCPDActivitiesListView.as_view(), name='enhanced-cpd-activities-list'),
    path('categories/', cpd_activity_categories, name='cpd-activity-categories'),
    path('search-suggestions/', cpd_activity_search_suggestions, name='cpd-activity-search-suggestions'),
    path('manual/', CreateManualCPDActivityView.as_view(), name='create-manual-cpd-activity'),
    path('my-manual/', UserManualCPDActivitiesView.as_view(), name='user-manual-cpd-activities'),
    path('recorded-webinars/', ListRecordedWebinarsView.as_view(), name='recorded-webinars-list'),
    
    # Provider endpoints
    path('my/', ProviderCPDActivitiesListView.as_view(), name='provider-cpd-activities'),
    path('create/', CreateProviderCPDActivityView.as_view(), name='create-provider-cpd-activity'),
    path('stats/', provider_stats, name='provider-stats'),
    path('<str:id>/delete/', ProviderCPDActivityDestroyView.as_view(), name='provider-cpd-activity-delete'),
    path('<str:id>/', CPDActivityDetailView.as_view(), name='cpd-activity-detail'),
]