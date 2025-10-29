from django.urls import path
from .views import (
    AvailableProgramsListView,
    ProgramDetailView,
    UserEnrollmentListView,
    UserActiveEnrollmentsView,
    UserArchivedEnrollmentsView,
    UserAllEnrollmentsView,
    ProgramEnrollmentView,
    EnrollmentDetailView,
    EnrollmentManagementView,
    EnrollmentCycleUpdateView,
    program_categories,
    multiple_program_categories,
    enrollment_categories,
)


urlpatterns = [
    path('enrollments/', UserEnrollmentListView.as_view(), name='user-enrollments'),
    path('enrollments/active/', UserActiveEnrollmentsView.as_view(), name='user-active-enrollments'),
    path('enrollments/archived/', UserArchivedEnrollmentsView.as_view(), name='user-archived-enrollments'),
    path('enrollments/all/', UserAllEnrollmentsView.as_view(), name='user-all-enrollments'),
    path('enrollments/categories/', enrollment_categories, name='enrollment-categories'),
    path('enroll/', ProgramEnrollmentView.as_view(), name='program-enroll'),
    path('enrollments/<str:pk>/', EnrollmentDetailView.as_view(), name='enrollment-detail'),
    path('enrollments/<str:pk>/manage/', EnrollmentManagementView.as_view(), name='enrollment-manage'),
    path('enrollments/<str:pk>/update-cycle/', EnrollmentCycleUpdateView.as_view(), name='enrollment-update-cycle'),
    
    path('categories/multiple/', multiple_program_categories, name='multiple-program-categories'),
    path('<str:program_id>/categories/', program_categories, name='program-categories'),
    
    path('', AvailableProgramsListView.as_view(), name='available-programs'),
    path('<slug:slug>/', ProgramDetailView.as_view(), name='program-detail'),
]