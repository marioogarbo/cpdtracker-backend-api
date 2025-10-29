from django.conf import settings
from djoser.social.views import ProviderAuthView
from rest_framework import status,  generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from .models import Profession
from .serializers import (
    OnboardingSerializer,
    UserProfileSerializer,
    CustomTokenObtainPairSerializer
)
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page


class OnboardingView(generics.UpdateAPIView):
    serializer_class = OnboardingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user.role = serializer.validated_data.get('role')

        if user.role == 'professional':
            user.profession = serializer.validated_data.get('profession')
            user.license_number = serializer.validated_data.get('license_number', '')
        user.is_onboarded = True
        user.save()
        return Response({'success': 'User onboarded successfully'}, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(cache_page(60 * 15, key_prefix='user_profile'))
    def dispatch(self, *args, **kwargs):
        # Cache the user profile for 15 minutes per user
        return super().dispatch(*args, **kwargs)

    def get_object(self):
        return self.request.user
    
    def get(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(user)
        return Response(serializer.data)


class CustomProviderAuthView(ProviderAuthView):
    def get(self, request, *args, **kwargs):
        # Handle GET request to get authorization URL
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 201:
            access_token = response.data.get('access')
            refresh_token = response.data.get('refresh')

            response.set_cookie(
                'access',
                access_token,
                max_age=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
                secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
                httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
                path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
                samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
            )

            response.set_cookie(
                'refresh',
                refresh_token,
                max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
                secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
                httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
                path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
                samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
            )
        return response


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            access_token = response.data.get('access')
            refresh_token = response.data.get('refresh')

            response.set_cookie(
                'access',
                access_token,
                max_age=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
                secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
                httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
                path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
                samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
            )

            response.set_cookie(
                'refresh',
                refresh_token,
                max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
                secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
                httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
                path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
                samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
            )
        return response


class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh')

        if refresh_token:
            request.data['refresh'] = refresh_token
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            access_token = response.data.get('access')
            response.set_cookie(
                'access',
                access_token,
                max_age=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
                secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
                httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
                path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
                samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
            )
        return response


class CustomTokenVerifyView(TokenVerifyView):
    def post(self, request, *args, **kwargs):
        access_token = request.COOKIES.get('access')

        if access_token:
            request.data['token'] = access_token
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            access_token = response.data.get('access')
            response.set_cookie(
                'access',
                access_token,
                max_age=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
                secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
                httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
                path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
                samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
            )
        return response


class LogoutView(APIView):
    def post(self, request, *args, **kwargs):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie('access')
        response.delete_cookie('refresh')
        return response


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_professions(request):
    """Return list of all available professions."""

    professions = Profession.objects.all().order_by('name')
    data = [
        {
            'id': profession.id,
            'name': profession.name
        }
        for profession in professions
    ]
    return Response(data)