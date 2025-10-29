from django.shortcuts import render
from rest_framework import generics, permissions, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Q
from .models import CPDLogEntry, CPDLogDetails, Evidence
from .serializers import CPDLogEntryListSerializer, CPDLogEntrySerializer, EvidenceSerializer
from cpd_managements.models import Enrollment
from cpd_activities.models import CPDActivity
from rest_framework import serializers


class IsProfessional(permissions.BasePermission):
    """
    Custom permission to only allow users with 'professional' role.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'role') and 
            request.user.role == 'professional'
        )


class CPDLogEntryListView(generics.ListAPIView):
    """
    List all CPD log entries for the current user.
    """
    serializer_class = CPDLogEntryListSerializer
    permission_classes = [permissions.IsAuthenticated, IsProfessional]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_manual', 'activity_type']
    search_fields = ['cpd_activity__title', 'notes']
    ordering_fields = ['completed_at', 'created_at', 'hours_spent']
    ordering = ['-completed_at']
    
    def get_queryset(self):
        return CPDLogEntry.objects.filter(user=self.request.user).select_related('cpd_activity')


class CPDLogEntryDetailView(generics.RetrieveAPIView):
    """
    Retrieve detailed information about a specific CPD log entry.
    """
    serializer_class = CPDLogEntrySerializer
    permission_classes = [permissions.IsAuthenticated, IsProfessional]
    
    def get_queryset(self):
        return CPDLogEntry.objects.filter(user=self.request.user).prefetch_related(
            'log_details__enrollment__program', 'evidences'
        )


class CreateCPDLogEntryView(generics.CreateAPIView):
    """
    Create a new CPD log entry.
    """
    serializer_class = CPDLogEntrySerializer
    permission_classes = [permissions.IsAuthenticated, IsProfessional]
    
    def create(self, request, *args, **kwargs):
        import logging
        logger = logging.getLogger(__name__)
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            log_entry = serializer.save()
            return Response({
                'message': 'CPD log entry created successfully.',
                'log_entry': CPDLogEntrySerializer(log_entry, context=self.get_serializer_context()).data
            }, status=status.HTTP_201_CREATED)
        except serializers.ValidationError as ve:
            logger.warning(f"Validation error creating CPD log entry: {ve}")
            return Response({'error': ve.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error creating CPD log entry: {e}", exc_info=True)
            return Response({'error': 'An unexpected error occurred while creating the CPD log entry.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateCPDLogEntryView(generics.UpdateAPIView):
    """
    Update an existing CPD log entry.
    """
    serializer_class = CPDLogEntrySerializer
    permission_classes = [permissions.IsAuthenticated, IsProfessional]
    
    def get_queryset(self):
        # Allow updates for all user's log entries
        return CPDLogEntry.objects.filter(user=self.request.user)


class CPDLogEntryEvidenceView(generics.ListCreateAPIView):
    """
    List and create evidence for a specific CPD log entry.
    """
    serializer_class = EvidenceSerializer
    permission_classes = [permissions.IsAuthenticated, IsProfessional]
    
    def get_queryset(self):
        log_entry_id = self.kwargs['log_entry_id']
        return Evidence.objects.filter(
            log_entry_id=log_entry_id,
            log_entry__user=self.request.user
        )
    
    def perform_create(self, serializer):
        log_entry_id = self.kwargs['log_entry_id']
        log_entry = CPDLogEntry.objects.get(
            id=log_entry_id,
            user=self.request.user
        )
        serializer.save(log_entry=log_entry)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsProfessional])
def user_cpd_summary(request):
    """
    Get CPD summary for the current user across all enrollments.
    """
    user = request.user
    
    # Get all active enrollments
    enrollments = Enrollment.objects.filter(user=user, status='active').select_related('program')
    
    summary = []
    for enrollment in enrollments:
        program_summary = {
            'enrollment_id': enrollment.id,
            'program': {
                'id': enrollment.program.id,
                'name': enrollment.program.name,
                'provider': enrollment.program.provider,
                'methodology': enrollment.program.methodology,
            },
            'cycle_info': {
                'start_date': enrollment.cycle_start_date,
                'end_date': enrollment.cycle_end_date,
                'is_active': enrollment.is_current_cycle_active,
            },
            'progress': {
                'accumulated_hours': float(enrollment.accumulated_hours),
                'accumulated_points': float(enrollment.accumulated_points),
                'required_hours': float(enrollment.program.required_hours),
                'required_points': float(enrollment.program.required_points),
            },
            'recent_activities': []
        }
        
        # Get recent activities for this enrollment
        recent_details = CPDLogDetails.objects.filter(
            enrollment=enrollment
        ).select_related('log_entry__cpd_activity').order_by('-log_entry__completed_at')[:5]
        
        for detail in recent_details:
            program_summary['recent_activities'].append({
                'activity_title': detail.log_entry.cpd_activity.title if detail.log_entry.cpd_activity else 'Manual Entry',
                'completed_at': detail.log_entry.completed_at,
                'hours': float(detail.total_hours),
                'points': float(detail.total_points),
            })
        
        summary.append(program_summary)
    
    return Response({'enrollments': summary})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsProfessional])
def enrollment_progress(request, enrollment_id):
    """
    Get detailed progress for a specific enrollment.
    """
    try:
        enrollment = Enrollment.objects.get(
            id=enrollment_id,
            user=request.user
        ).select_related('program')
    except Enrollment.DoesNotExist:
        return Response({'error': 'Enrollment not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get all log details for this enrollment
    log_details = CPDLogDetails.objects.filter(
        enrollment=enrollment
    ).select_related('log_entry__cpd_activity').order_by('-log_entry__completed_at')
    
    activities = []
    for detail in log_details:
        activities.append({
            'log_entry_id': detail.log_entry.id,
            'activity_title': detail.log_entry.cpd_activity.title if detail.log_entry.cpd_activity else 'Manual Entry',
            'activity_type': detail.log_entry.activity_type,
            'completed_at': detail.log_entry.completed_at,
            'hours': float(detail.total_hours),
            'points': float(detail.total_points),
            'status': detail.status,
        })
    
    progress_data = {
        'enrollment': {
            'id': enrollment.id,
            'program_name': enrollment.program.name,
            'cycle_start': enrollment.cycle_start_date,
            'cycle_end': enrollment.cycle_end_date,
            'is_active': enrollment.is_current_cycle_active,
        },
        'progress': {
            'accumulated_hours': float(enrollment.accumulated_hours),
            'accumulated_points': float(enrollment.accumulated_points),
            'required_hours': float(enrollment.program.required_hours),
            'required_points': float(enrollment.program.required_points),
            'hours_remaining': float(enrollment.program.required_hours - enrollment.accumulated_hours),
            'points_remaining': float(enrollment.program.required_points - enrollment.accumulated_points),
        },
        'activities': activities
    }
    
    return Response(progress_data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsProfessional])
def cpd_workflow_data(request):
    """
    Get all necessary data for the CPD logging workflow in a single call.
    """
    user = request.user
    
    # Get user enrollments
    enrollments = Enrollment.objects.filter(
        user=user, 
        status='active'
    ).select_related('program')
    
    user_enrollments = []
    for enrollment in enrollments:
        user_enrollments.append({
            'id': enrollment.id,
            'program_id': enrollment.program.id,
            'program_name': enrollment.program.name,
            'program_provider': enrollment.program.provider,
            'methodology': enrollment.program.methodology,
            'cycle_start_date': enrollment.cycle_start_date.isoformat(),
            'cycle_end_date': enrollment.cycle_end_date.isoformat(),
            'is_active': enrollment.is_current_cycle_active,
            'accumulated_hours': float(enrollment.accumulated_hours),
            'accumulated_points': float(enrollment.accumulated_points),
        })
    
    # Get available approved CPD activities
    activities = CPDActivity.objects.filter(status='approved')
    
    available_activities = []
    for activity in activities:
        available_activities.append({
            'id': activity.id,
            'title': activity.title,
            'provider': activity.provider or '',
            'activity_type': activity.activity_type,
            'activity_type_display': activity.get_activity_type_display(),
            'default_points_per_hour': float(activity.default_points_per_hour),
            'start_datetime': activity.start_datetime.isoformat() if activity.start_datetime else None,
            'end_datetime': activity.end_datetime.isoformat() if activity.end_datetime else None,
            'description': activity.description or '',
        })
    
    # Activity categories
    activity_categories = [
        {'value': choice[0], 'label': choice[1]} 
        for choice in CPDLogEntry.ACTIVITY_TYPE_CHOICES
    ]
    
    # Recent log entries
    recent_entries = CPDLogEntry.objects.filter(
        user=user
    ).select_related('cpd_activity').order_by('-completed_at')[:5]
    
    recent_log_entries = []
    for entry in recent_entries:
        recent_log_entries.append({
            'id': entry.id,
            'title': entry.cpd_activity.title if entry.cpd_activity else 'Manual Entry',
            'provider': entry.cpd_activity.provider if entry.cpd_activity else '',
            'hours_spent': float(entry.hours_spent),
            'completed_at': entry.completed_at.isoformat(),
            'is_manual': entry.is_manual,
            'activity_type': entry.activity_type,
        })
    
    workflow_data = {
        'user_enrollments': user_enrollments,
        'available_activities': available_activities,
        'activity_categories': activity_categories,
        'recent_log_entries': recent_log_entries,
        'workflow_info': {
            'total_enrollments': len(user_enrollments),
            'available_activities_count': len(available_activities),
            'user_profession': user.profession.name if hasattr(user, 'profession') and user.profession else None,
        }
    }
    
    return Response(workflow_data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsProfessional])
def preview_activity_points(request):
    """
    Preview points calculation for an activity assignment to specific programs with categories.
    """
    activity_id = request.GET.get('activity_id')
    program_enrollment_ids = request.GET.getlist('program_enrollment_ids[]')
    hours_spent = request.GET.get('hours_spent', '1.0')
    
    # Handle program categories - expect format: enrollment_id:category_code
    program_categories = {}
    for key, value in request.GET.items():
        if key.startswith('program_categories[') and key.endswith(']'):
            enrollment_id = key[len('program_categories['):-1]
            program_categories[enrollment_id] = value
    
    try:
        hours_spent = float(hours_spent)
    except (ValueError, TypeError):
        return Response(
            {'error': 'Invalid hours_spent value'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not program_enrollment_ids:
        return Response(
            {'error': 'At least one program enrollment ID is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get user enrollments
    enrollments = Enrollment.objects.filter(
        id__in=program_enrollment_ids,
        user=request.user,
        status='active'
    ).select_related('program')
    
    if len(enrollments) != len(program_enrollment_ids):
        return Response(
            {'error': 'One or more enrollment IDs are invalid'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get activity if provided
    activity = None
    if activity_id:
        try:
            activity = CPDActivity.objects.get(id=activity_id, status='approved')
        except CPDActivity.DoesNotExist:
            return Response(
                {'error': 'Activity not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Calculate points for each program
    program_calculations = []
    for enrollment in enrollments:
        # Mock calculation similar to CPDLogDetails.calculate_points()
        from decimal import Decimal
        from cpd_managements.models import CredentialCriteria
        
        points_per_hour = Decimal('1.0')  # Default
        criteria_used = None
        lookup_category = None
        
        # Check if program-specific category was selected
        if enrollment.id in program_categories:
            category_identifier = program_categories[enrollment.id]
            try:
                # Check if the category_identifier is an ID (starts with 'rule_') or a code (legacy)
                if category_identifier.startswith('rule_'):
                    # It's a CredentialCriteria ID - look up by ID
                    criteria = CredentialCriteria.objects.get(
                        id=category_identifier,
                        program=enrollment.program
                    )
                else:
                    # It's a category code - look up by code (legacy support)
                    criteria = CredentialCriteria.objects.get(
                        program=enrollment.program,
                        category_code=category_identifier
                    )
                
                points_per_hour = criteria.points_per_hour
                criteria_used = criteria.category_name
            except CredentialCriteria.DoesNotExist:
                # Category not found, use default
                pass
        elif activity:
            # Fallback: try to match by activity type (for legacy support)
            lookup_category = activity.activity_type
            try:
                criteria = CredentialCriteria.objects.get(
                    program=enrollment.program,
                    category_code=activity.activity_type
                )
                points_per_hour = criteria.points_per_hour
                criteria_used = criteria.category_name
            except CredentialCriteria.DoesNotExist:
                # Use activity default points per hour if available
                if activity.default_points_per_hour:
                    points_per_hour = activity.default_points_per_hour
        
        total_points = Decimal(str(hours_spent)) * points_per_hour
        
        program_calculations.append({
            'enrollment_id': enrollment.id,
            'program_name': enrollment.program.name,
            'program_methodology': enrollment.program.get_methodology_display(),
            'points_per_hour': float(points_per_hour),
            'total_points': float(total_points),
            'hours_counted': hours_spent,
            'current_accumulated_hours': float(enrollment.accumulated_hours),
            'current_accumulated_points': float(enrollment.accumulated_points),
            'criteria_used': criteria_used,
            'lookup_category': lookup_category,
            'selected_category': program_categories.get(enrollment.id, None),
        })
    
    response_data = {
        'activity_title': activity.title if activity else 'Manual Entry',
        'hours_spent': hours_spent,
        'program_calculations': program_calculations,
        'total_points_all_programs': sum(p['total_points'] for p in program_calculations),
    }
    
    return Response(response_data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsProfessional])
def user_cpd_logbook(request):
    """
    Get complete CPD logbook for the current user with comprehensive program details.
    Optionally filter by enrollment_id if provided.
    Always returns a valid response, even if the user has no activities.
    """
    import logging
    logger = logging.getLogger(__name__)
    user = request.user
    enrollment_id = request.GET.get('enrollment_id')

    try:
        # Base queryset for log entries
        log_entries_queryset = CPDLogEntry.objects.filter(user=user).select_related('cpd_activity').prefetch_related(
            'log_details__enrollment__program',
            'log_details__applied_criteria',
            'evidences'
        )

        # Base queryset for log details
        log_details_queryset = CPDLogDetails.objects.filter(log_entry__user=user)

        # Filter by enrollment if specified
        if enrollment_id:
            log_entries_queryset = log_entries_queryset.filter(
                log_details__enrollment_id=enrollment_id
            ).distinct()
            log_details_queryset = log_details_queryset.filter(
                enrollment_id=enrollment_id
            )

        # Order the log entries
        log_entries = log_entries_queryset.order_by('-completed_at', '-created_at')

        # Import the new serializer
        from .serializers import CPDLogbookEntrySerializer

        # Serialize the log entries with comprehensive data
        serializer = CPDLogbookEntrySerializer(log_entries, many=True)
        logbook_entries = serializer.data if serializer.data is not None else []

        # Calculate totals from log details
        totals = log_details_queryset.aggregate(
            total_hours=Sum('total_hours'),
            total_points=Sum('total_points')
        )
        total_hours = float(totals['total_hours'] or 0)
        total_points = float(totals['total_points'] or 0)

        return Response({
            'total_hours': total_hours,
            'total_cpd_points': total_points,
            'logbook_entries': logbook_entries
        })
    except Exception as e:
        logger.error(f"Error in user_cpd_logbook: {e}")
        # Always return a valid empty logbook for new users or on error
        return Response({
            'total_hours': 0.0,
            'total_cpd_points': 0.0,
            'logbook_entries': []
        })


class DeleteCPDLogEntryView(generics.DestroyAPIView):
    """
    Delete an existing CPD log entry.
    """
    serializer_class = CPDLogEntrySerializer
    permission_classes = [permissions.IsAuthenticated, IsProfessional]
    
    def get_queryset(self):
        # Allow deletion for all user's log entries
        return CPDLogEntry.objects.filter(user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Store some info for the response
        entry_title = instance.title
        entry_id = instance.id
        
        # Perform the deletion
        self.perform_destroy(instance)
        
        return Response({
            'message': f'CPD log entry "{entry_title}" deleted successfully.',
            'deleted_entry_id': entry_id
        }, status=status.HTTP_200_OK)