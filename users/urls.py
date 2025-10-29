from django.urls import path
from .views import (
    UserProfileView, OnboardingView, LogoutView,
    CustomProviderAuthView, CustomTokenObtainPairView,
    CustomTokenRefreshView, CustomTokenVerifyView,
    get_professions,
)

urlpatterns = [
    path('o/<str:provider>/callback', CustomProviderAuthView.as_view(), name='social_auth'),
    path('auth/jwt/create/', CustomTokenObtainPairView.as_view()),
    path('auth/jwt/refresh/', CustomTokenRefreshView.as_view()),
    path('auth/jwt/verify/', CustomTokenVerifyView.as_view()),
    path('auth/logout/', LogoutView.as_view()),
    path('auth/professions/', get_professions, name='professions-list'),
    path('users/onboarding/', OnboardingView.as_view()),
    path('users/me/', UserProfileView.as_view()),
]