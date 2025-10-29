from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from .serializers import ProgramListSerializer, ProgramDetailSerializer, EnrollmentSerializer, CredentialCriteriaSerializer
from .services.program_service import ProgramService
from .services.enrollment_service import EnrollmentService
from .services.category_service import CategoryService
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page


class IsProfessional(permissions.BasePermission):
    """
    Custom permission to only allow users with 'professional' role.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role == 'professional'
    

class AvailableProgramsListView(generics.ListAPIView):
    """
    List all active credentialing programs available for enrollment.
    (Cached for 15 minutes)
    """
    serializer_class = ProgramListSerializer
    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(cache_page(60 * 15, key_prefix='available_programs'))
    def dispatch(self, *args, **kwargs):
        # Cache the available programs list for 15 minutes for all users
        return super().dispatch(*args, **kwargs)
    
    def get_queryset(self):
        return ProgramService.get_active_programs()


class ProgramDetailView(generics.RetrieveAPIView):
    """
    Retrieve detailed information about a specific credentialing program.
    (Cached for 15 minutes per program)
    """
    serializer_class = ProgramDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsProfessional]
    lookup_field = 'slug'

    @method_decorator(cache_page(60 * 15, key_prefix='program_detail'))
    def dispatch(self, *args, **kwargs):
        # Cache the program detail for 15 minutes per program
        return super().dispatch(*args, **kwargs)
    
    def get_queryset(self):
        return ProgramService.get_active_programs()


class UserEnrollmentListView(generics.ListAPIView):
    """
    List all programs the current user is enrolled in (excluding deleted and archived).
    """
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsProfessional]
    
    def get_queryset(self):
        return EnrollmentService.get_user_enrollments(
            self.request.user, 
            status_filter=['active', 'completed']
        )


class UserActiveEnrollmentsView(generics.ListAPIView):
    """
    List all active programs the current user is enrolled in.
    """
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsProfessional]
    
    def get_queryset(self):
        return EnrollmentService.get_user_active_enrollments(self.request.user)


class UserArchivedEnrollmentsView(generics.ListAPIView):
    """
    List all archived programs the current user is enrolled in.
    """
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsProfessional]
    
    def get_queryset(self):
        return EnrollmentService.get_user_archived_enrollments(self.request.user)


class UserAllEnrollmentsView(generics.ListAPIView):
    """
    List all enrollments including archived (but not deleted) for management purposes.
    """
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsProfessional]
    
    def get_queryset(self):
        return EnrollmentService.get_user_all_enrollments(self.request.user)


class ProgramEnrollmentView(generics.CreateAPIView):
    """
    Enroll a professional user in a credentialing program.
    """
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsProfessional]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            # The user is automatically set in the serializer's create method
            enrollment = serializer.save()
            
            return Response({
                'message': f'Successfully enrolled in {enrollment.program.name}',
                'enrollment': EnrollmentSerializer(enrollment, context=self.get_serializer_context()).data
            }, status=status.HTTP_201_CREATED)
            
        except serializers.ValidationError as e:
            # Handle validation errors specifically
            error_message = "Validation failed"
            if hasattr(e, 'detail'):
                if isinstance(e.detail, dict):
                    # Extract program-specific errors
                    if 'program' in e.detail:
                        error_message = e.detail['program'][0] if isinstance(e.detail['program'], list) else str(e.detail['program'])
                    elif 'non_field_errors' in e.detail:
                        error_message = e.detail['non_field_errors'][0] if isinstance(e.detail['non_field_errors'], list) else str(e.detail['non_field_errors'])
                    else:
                        # Get the first error message
                        for field, errors in e.detail.items():
                            if isinstance(errors, list) and errors:
                                error_message = f"{field}: {errors[0]}"
                            else:
                                error_message = f"{field}: {errors}"
                            break
                elif isinstance(e.detail, list) and e.detail:
                    error_message = str(e.detail[0])
                else:
                    error_message = str(e.detail)
            
            return Response({
                'message': error_message,
                'error': 'validation_failed'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            # Log the actual error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Enrollment creation failed: {str(e)}")
            
            # Return more specific error messages
            if "unique constraint" in str(e).lower() or "already exists" in str(e).lower():
                return Response({
                    'message': 'You are already enrolled in this program with the same start date.',
                    'error': 'duplicate_enrollment'
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    'message': f'Failed to create enrollment: {str(e)}',
                    'error': 'enrollment_creation_failed'
                }, status=status.HTTP_400_BAD_REQUEST)


class EnrollmentDetailView(generics.RetrieveAPIView):
    """
    Retrieve detailed information about a specific enrollment.
    """
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsProfessional]
    
    def get_queryset(self):
        return EnrollmentService.get_user_enrollments(self.request.user)


class EnrollmentManagementView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update an enrollment (e.g., mark as completed, cancelled, archived, deleted).
    """
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsProfessional]
    
    def get_queryset(self):
        return EnrollmentService.get_user_enrollments(self.request.user)
    
    def partial_update(self, request, *args, **kwargs):
        """Allow partial updates to enrollment status."""
        enrollment = self.get_object()
        
        # Get the action from the request
        action = request.data.get('action')
        new_status = request.data.get('status')
        
        if action:
            # Handle specific actions using service layer
            if action == 'delete':
                success, message = EnrollmentService.delete_enrollment(enrollment)
            elif action == 'archive':
                success, message = EnrollmentService.archive_enrollment(enrollment)
            elif action == 'reactivate':
                success, message = EnrollmentService.reactivate_enrollment(enrollment)
            else:
                return Response({
                    'message': 'Invalid action. Allowed values: delete, archive, reactivate',
                    'error': 'invalid_action'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if success:
                return Response({
                    'message': message,
                    'enrollment': EnrollmentSerializer(enrollment, context={'request': request}).data
                })
            else:
                return Response({
                    'message': message,
                    'error': 'action_failed'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        elif new_status:
            # Handle direct status updates (legacy support)
            success, message = EnrollmentService.update_enrollment_status(enrollment, new_status)
            
            if success:
                return Response({
                    'message': message,
                    'enrollment': EnrollmentSerializer(enrollment, context={'request': request}).data
                })
            else:
                return Response({
                    'message': message,
                    'error': 'status_update_failed'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'message': 'Either action or status must be provided',
                'error': 'missing_action_or_status'
            }, status=status.HTTP_400_BAD_REQUEST)


class EnrollmentCycleUpdateView(generics.UpdateAPIView):
    """
    Update the cycle start date of an enrollment.
    This will recalculate the cycle end date based on the program's renewal period.
    """
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsProfessional]
    
    def get_queryset(self):
        return EnrollmentService.get_user_enrollments(self.request.user)
    
    def patch(self, request, *args, **kwargs):
        """Update enrollment cycle start date."""
        enrollment = self.get_object()
        new_cycle_start_date = request.data.get('cycle_start_date')
        
        if not new_cycle_start_date:
            return Response({
                'message': 'cycle_start_date is required',
                'error': 'missing_cycle_start_date'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Use service layer to update cycle start date
        success, message = EnrollmentService.update_cycle_start_date(
            enrollment, new_cycle_start_date
        )
        
        if success:
            return Response({
                'message': message,
                'enrollment': EnrollmentSerializer(enrollment, context={'request': request}).data
            })
        else:
            return Response({
                'message': message,
                'error': 'update_failed'
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def program_categories(request, program_id):
    """
    Get all available categories for a specific credentialing program.
    """
    program = ProgramService.get_program_by_id(program_id)
    
    if not program:
        return Response({'error': 'Program not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get categories using service layer
    categories = CategoryService.get_program_categories(program)
    serializer = CredentialCriteriaSerializer(categories, many=True)
    
    return Response({
        'program_id': program.id,
        'program_name': program.name,
        'categories': serializer.data
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def multiple_program_categories(request):
    """
    Get categories for multiple programs in a single request.
    Expects: {"program_ids": ["program_123", "program_456"]}
    """
    program_ids = request.data.get('program_ids', [])
    
    if not program_ids:
        return Response({'error': 'program_ids is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Use service layer to get multiple program categories
    result = ProgramService.get_multiple_program_categories(program_ids)
    
    # Serialize the categories
    for program_id, data in result.items():
        data['categories'] = CredentialCriteriaSerializer(data['categories'], many=True).data
    
    return Response(result)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def enrollment_categories(request):
    """
    Get categories for all user's active enrollments.
    This is useful for the "Continue to Programs" workflow.
    """
    # Use service layer to get enrollment categories
    enrollments_data = CategoryService.get_enrollment_categories(request.user)
    
    # Serialize the categories
    for enrollment_data in enrollments_data:
        enrollment_data['categories'] = CredentialCriteriaSerializer(
            enrollment_data['categories'], many=True
        ).data
    
    return Response({
        'enrollments': enrollments_data,
        'total_enrollments': len(enrollments_data)
    })