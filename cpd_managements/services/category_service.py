from ..models import CredentialCriteria, Enrollment


class CategoryService:
    """Service class for category-related operations."""
    
    @staticmethod
    def get_program_categories(program):
        """Get all categories for a specific program, ordered by sort_order."""
        return CredentialCriteria.objects.filter(
            program=program
        ).order_by('sort_order', 'category_code')
    
    @staticmethod
    def get_enrollment_categories(user):
        """
        Get categories for all user's active enrollments.
        This is useful for the "Continue to Programs" workflow.
        """
        # Get user's active enrollments
        enrollments = Enrollment.objects.filter(
            user=user,
            status='active'
        ).select_related('program').prefetch_related('program__category_rules')
        
        result = []
        for enrollment in enrollments:
            categories = CategoryService.get_program_categories(enrollment.program)
            result.append({
                'enrollment_id': enrollment.id,
                'program_id': enrollment.program.id,
                'program_name': enrollment.program.name,
                'program_provider': enrollment.program.provider,
                'cycle_start_date': enrollment.cycle_start_date,
                'cycle_end_date': enrollment.cycle_end_date,
                'categories': categories
            })
        
        return result 