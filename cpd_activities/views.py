import requests
from django.shortcuts import render
from django.db.models import Q, Count, Case, When, IntegerField
from rest_framework import generics, permissions, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import CPDActivity
from .serializers import (
    CPDActivityListSerializer, 
    CPDActivityDetailSerializer,
    CreateManualCPDActivitySerializer,
    CreateProviderCPDActivitySerializer
)
from rest_framework.generics import DestroyAPIView
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page


class IsProfessional(permissions.BasePermission):
    """
    Custom permission to only allow users with 'professional' role.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'professional'
        )
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'professional'
        )


class IsProvider(permissions.BasePermission):
    """
    Custom permission to only allow users with 'provider' role.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'provider'
        )
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'provider'
        )


class ApprovedCPDActivitiesListView(generics.ListAPIView):
    """
    List all approved CPD activities available for selection by professionals.
    Supports filtering by activity type, provider, and search by title.
    For provider users, it will also indicate if an activity was created by them.
    """
    serializer_class = CPDActivityListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['activity_type', 'provider']
    search_fields = ['title', 'description', 'provider']
    ordering_fields = ['title', 'created_at', 'start_datetime']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return only approved, non-manual activities."""
        user = self.request.user
        queryset = CPDActivity.objects.filter(
            status='approved',
            is_manual=False
        ).prefetch_related('recommended_professions')
        
        # Optional profession-based filtering for professionals
        if user.role == 'professional' and hasattr(user, 'profession') and user.profession:
            profession_filter = self.request.query_params.get('profession_filter', 'true').lower()
            if profession_filter == 'true':
                queryset = queryset.filter(Q(recommended_professions=user.profession) | Q(recommended_professions__isnull=True))
        
        # If profession_filter is false or not specified, show all approved activities
        
        # Filter by upcoming events only
        show_upcoming_only = self.request.query_params.get('upcoming_only', 'false').lower()
        if show_upcoming_only == 'true':
            from django.utils import timezone
            queryset = queryset.filter(
                Q(start_datetime__gte=timezone.now()) |
                Q(start_datetime__isnull=True)
            )
        
        return queryset

    def get_serializer_context(self):
        """Pass request to serializer context."""
        return {'request': self.request}


class CPDActivityDetailView(generics.RetrieveAPIView):
    """
    Retrieve detailed information about a specific CPD activity.
    (Cached for 15 minutes per activity)
    """
    serializer_class = CPDActivityDetailSerializer
    permission_classes = [permissions.IsAuthenticated]  # Allow both professionals and providers
    lookup_field = 'id'

    @method_decorator(cache_page(60 * 15, key_prefix='cpd_activity_detail'))
    def dispatch(self, *args, **kwargs):
        # Cache the activity detail for 15 minutes per activity
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        """Return only approved activities."""
        return CPDActivity.objects.filter(
            status='approved'
        ).prefetch_related('recommended_professions').select_related('created_by')
    
    def get_serializer_context(self):
        """Pass request to serializer context."""
        return {'request': self.request}


class CreateManualCPDActivityView(generics.CreateAPIView):
    """
    Allow professionals to create manual CPD activities that need approval.
    """
    serializer_class = CreateManualCPDActivitySerializer
    permission_classes = [permissions.IsAuthenticated, IsProfessional]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        activity = serializer.save()
        
        return Response({
            'message': 'Manual CPD activity created successfully and submitted for approval.',
            'activity': CPDActivityDetailSerializer(activity, context=self.get_serializer_context()).data
        }, status=status.HTTP_201_CREATED)


class UserManualCPDActivitiesView(generics.ListAPIView):
    """
    List all manual CPD activities created by the current user.
    """
    serializer_class = CPDActivityListSerializer
    permission_classes = [permissions.IsAuthenticated, IsProfessional]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'title', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return only manual activities created by current user."""
        return CPDActivity.objects.filter(
            created_by=self.request.user,
            is_manual=True
        ).prefetch_related('recommended_professions')
    

class ListRecordedWebinarsView(generics.ListAPIView):
    """
    List all recorded webinar CPD activities available for professionals.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        """Return only approved recorded webinar activities."""
        try:
            url = "https://adair.stg.axcelerate.com/api/courses/"
            params = {"trainingArea": "FIA Microlearning", "displayLength": 100}
            headers = {
                "wstoken": '0984FBCE-1EB2-44C8-A3030768EDB7E1FE',
                "apitoken": '51A0BEF5-5362-4856-9ED902FAD93B9B0C'
            }
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return Response(data)
        except requests.Timeout:
            return Response({'error': 'Timeout fetching recorded webinars'}, status=status.HTTP_504_GATEWAY_TIMEOUT)
        except requests.RequestException as e:
            return Response({'error': 'Failed to fetch recorded webinars', 'details': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class ProviderCPDActivitiesListView(generics.ListAPIView):
    """
    List all CPD activities created by the current provider.
    """
    serializer_class = CPDActivityListSerializer
    permission_classes = [permissions.IsAuthenticated, IsProvider]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['activity_type', 'status']
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'created_at', 'start_datetime']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return only activities created by the current provider."""
        return CPDActivity.objects.filter(
            created_by=self.request.user
        ).prefetch_related('recommended_professions')


class CreateProviderCPDActivityView(generics.CreateAPIView):
    """
    Allow providers to create CPD activities for professionals to enroll in.
    """
    serializer_class = CreateProviderCPDActivitySerializer
    permission_classes = [permissions.IsAuthenticated, IsProvider]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        activity = serializer.save()
        
        return Response({
            'message': 'CPD activity created successfully and submitted for approval.',
            'activity': CPDActivityDetailSerializer(activity, context=self.get_serializer_context()).data
        }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsProfessional])
def cpd_activity_categories(request):
    """
    Return list of available CPD activity categories.
    """
    categories = [
        {'value': choice[0], 'label': choice[1]} 
        for choice in CPDActivity.ACTIVITY_TYPE_CHOICES
    ]
    return Response({'categories': categories})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsProfessional])
def cpd_activity_search_suggestions(request):
    """
    Provide search suggestions for CPD activities based on user's query.
    """
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return Response({'suggestions': []})
    
    # Get approved activities matching the query
    suggestions = CPDActivity.objects.filter(
        status='approved',
        is_manual=False,
        title__icontains=query
    ).values_list('title', flat=True)[:10]
    
    # Also get provider suggestions
    provider_suggestions = CPDActivity.objects.filter(
        status='approved',
        is_manual=False,
        provider__icontains=query
    ).values_list('provider', flat=True).distinct()[:5]
    
    return Response({
        'suggestions': {
            'titles': list(suggestions),
            'providers': list(provider_suggestions)
        }
    })
    if len(query) < 2:
        return Response({'suggestions': []})
    
    # Get unique providers and titles for suggestions
    activities = CPDActivity.objects.filter(
        status='approved',
        is_manual=False
    ).filter(
        Q(title__icontains=query) |
        Q(provider__icontains=query) |
        Q(description__icontains=query)
    )[:10]
    
    suggestions = []
    for activity in activities:
        suggestions.append({
            'id': activity.id,
            'title': activity.title,
            'provider': activity.provider,
            'type': 'activity'
        })
    
    # Add unique providers
    providers = CPDActivity.objects.filter(
        status='approved',
        is_manual=False,
        provider__icontains=query
    ).values_list('provider', flat=True).distinct()[:5]
    
    for provider in providers:
        if provider:
            suggestions.append({
                'title': provider,
                'type': 'provider'
            })
    
    return Response({'suggestions': suggestions})


class EnhancedCPDActivitiesListView(generics.ListAPIView):
    """
    Enhanced list view that returns CPD activities organized into recommended and other arrays
    for professional users based on their profession. Provides better UX for the frontend.
    """
    serializer_class = CPDActivityListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['activity_type', 'provider']
    search_fields = ['title', 'description', 'provider']
    ordering_fields = ['title', 'created_at', 'start_datetime']
    ordering = ['-created_at']

    @method_decorator(cache_page(60 * 15, key_prefix='enhanced_cpd_activities'))
    def dispatch(self, *args, **kwargs):
        # Cache the enhanced activities list for 15 minutes for all users
        return super().dispatch(*args, **kwargs)
    
    def get_queryset(self):
        """Return approved, non-manual activities with optimized queries."""
        return CPDActivity.objects.filter(
            status='approved',
            is_manual=False
        ).prefetch_related('recommended_professions').select_related('created_by')
    
    def list(self, request, *args, **kwargs):
        """Custom list method to organize activities based on user role."""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Apply additional filtering
        queryset = self._apply_additional_filters(queryset)
        
        user = request.user
        
        if user.role == 'professional':
            return self._get_professional_response(queryset, request)
        elif user.role == 'provider':
            return self._get_provider_response(queryset, request)
        else:
            # Admin or other roles get standard list
            return self._get_standard_response(queryset, request)
    
    def _apply_additional_filters(self, queryset):
        """Apply additional query parameter filters."""
        request = self.request
        
        # Filter by upcoming events only
        show_upcoming_only = request.query_params.get('upcoming_only', 'false').lower()
        if show_upcoming_only == 'true':
            from django.utils import timezone
            queryset = queryset.filter(
                Q(start_datetime__gte=timezone.now()) |
                Q(start_datetime__isnull=True)
            )
        
        return queryset
    
    def _get_professional_response(self, queryset, request):
        """Return organized response for professional users."""
        user = request.user
        
        # Split activities into recommended and other
        if hasattr(user, 'profession') and user.profession:
            # Activities recommended for user's profession
            recommended_queryset = queryset.filter(
                Q(recommended_professions=user.profession) | 
                Q(recommended_professions__isnull=True)  # Activities with no specific profession requirement
            ).distinct()
            
            # Activities NOT recommended for user's profession
            other_queryset = queryset.filter(
                ~Q(recommended_professions=user.profession)
            ).exclude(recommended_professions__isnull=True).distinct()
        else:
            # If user has no profession, treat all as "other"
            recommended_queryset = queryset.none()
            other_queryset = queryset
        
        # Apply pagination manually if needed
        page_size = self.get_page_size()
        if page_size is not None:
            # For this enhanced view, we'll return all results but you can implement pagination here
            pass
        
        # Serialize the data
        recommended_activities = self.get_serializer(recommended_queryset, many=True, context={'request': request}).data
        other_activities = self.get_serializer(other_queryset, many=True, context={'request': request}).data
        
        return Response({
            'recommended': recommended_activities,
            'other': other_activities,
            'total_count': len(recommended_activities) + len(other_activities),
            'recommended_count': len(recommended_activities),
            'other_count': len(other_activities),
            'user_profession': user.profession.name if hasattr(user, 'profession') and user.profession else None
        })
    
    def _get_provider_response(self, queryset, request):
        """Return response for provider users with created flag."""
        # All activities with created_by_provider flag
        activities = self.get_serializer(queryset, many=True, context={'request': request}).data
        
        return Response({
            'activities': activities,
            'total_count': len(activities)
        })
    
    def _get_standard_response(self, queryset, request):
        """Return standard paginated response for admin/other roles."""
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response({
            'activities': serializer.data,
            'total_count': len(serializer.data)
        })

    def get_page_size(self):
        """Get page size from query params or default."""
        try:
            page_size = int(self.request.query_params.get('page_size', 50))
            return min(page_size, 100)  # Max 100 items per page
        except (ValueError, TypeError):
            return 50


class ProviderCPDActivityStatsView(generics.GenericAPIView):
    """
    Provide actual statistics for the current provider regarding their CPD activities.
    
    Returns metrics like:
    - total activities created
    - total approved
    - total pending approval
    - total rejected
    - approval rate
    """
    permission_classes = [permissions.IsAuthenticated, IsProvider]
    
    def get(self, request, *args, **kwargs):
        user = request.user
        
        # Aggregate statistics
        stats = CPDActivity.objects.filter(
            created_by=user
        ).aggregate(
            total_activities=Count('id'),
            total_approved=Count(Case(
                When(status='approved', then=1),
                output_field=IntegerField()
            )),
            total_pending=Count(Case(
                When(status='pending', then=1),
                output_field=IntegerField()
            )),
            total_rejected=Count(Case(
                When(status='rejected', then=1),
                output_field=IntegerField()
            ))
        )
        
        # Calculate approval rate
        total_activities = stats['total_activities'] or 1  # Avoid division by zero
        approval_rate = (stats['total_approved'] or 0) / total_activities * 100
        
        return Response({
            'stats': {
                'total_activities': stats['total_activities'],
                'total_approved': stats['total_approved'],
                'total_pending': stats['total_pending'],
                'total_rejected': stats['total_rejected'],
                'approval_rate': round(approval_rate, 2)
            }
        })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsProvider])
def provider_stats(request):
    """
    Return statistics about activities created by the current provider.
    """
    user = request.user
    
    # Get all activities created by the provider
    activities = CPDActivity.objects.filter(created_by=user)
    
    # Calculate statistics
    stats = activities.aggregate(
        total_activities=Count('id'),
        pending_activities=Count(Case(When(status='pending', then=1), output_field=IntegerField())),
        approved_activities=Count(Case(When(status='approved', then=1), output_field=IntegerField())),
        rejected_activities=Count(Case(When(status='rejected', then=1), output_field=IntegerField()))
    )
    
    return Response(stats)


class ProviderCPDActivityDestroyView(DestroyAPIView):
    """
    Allow providers to delete their own CPD activities.
    """
    serializer_class = CPDActivityDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsProvider]
    lookup_field = 'id'

    def get_queryset(self):
        # Only allow deleting activities created by the current provider
        return CPDActivity.objects.filter(created_by=self.request.user)