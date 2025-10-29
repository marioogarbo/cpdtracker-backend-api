from django.urls import path
from .views import (
    CPDLogEntryListView,
    CPDLogEntryDetailView,
    CreateCPDLogEntryView,
    UpdateCPDLogEntryView,
    DeleteCPDLogEntryView,
    CPDLogEntryEvidenceView,
    user_cpd_summary,
    user_cpd_logbook,
    enrollment_progress,
    cpd_workflow_data,
    preview_activity_points,
)

urlpatterns = [
    path('enrollment/<str:enrollment_id>/progress/', enrollment_progress, name='enrollment-progress'),
    path('workflow-data/', cpd_workflow_data, name='cpd-workflow-data'),
    path('preview-points/', preview_activity_points, name='preview-activity-points'),
    path('logbook/', user_cpd_logbook, name='user-cpd-logbook'),
    path('log/', CreateCPDLogEntryView.as_view(), name='create-cpd-log-entry-main'),
    path('summary/', user_cpd_summary, name='user-cpd-summary'),

    path('', CPDLogEntryListView.as_view(), name='cpd-log-entries'),
    path('create/', CreateCPDLogEntryView.as_view(), name='create-cpd-log-entry'),
    path('<str:pk>/', CPDLogEntryDetailView.as_view(), name='cpd-log-entry-detail'),
    path('<str:pk>/update/', UpdateCPDLogEntryView.as_view(), name='update-cpd-log-entry'),
    path('<str:pk>/delete/', DeleteCPDLogEntryView.as_view(), name='delete-cpd-log-entry'),
    path('<str:log_entry_id>/evidence/', CPDLogEntryEvidenceView.as_view(), name='cpd-log-entry-evidence'),
]