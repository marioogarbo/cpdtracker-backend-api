from django.utils import timezone
from ..models import CredentialingProgram, CredentialCriteria


class ProgramService:
    """Service class for program-related operations."""
    
    @staticmethod
    def get_active_programs():
        """Get all active credentialing programs."""
        return CredentialingProgram.objects.filter(status='active')
    
    @staticmethod
    def get_program_by_slug(slug):
        """Get a specific program by its slug."""
        try:
            return CredentialingProgram.objects.filter(
                status='active'
            ).prefetch_related('category_rules').get(slug=slug)
        except CredentialingProgram.DoesNotExist:
            return None
    
    @staticmethod
    def get_program_by_id(program_id):
        """Get a specific program by its ID."""
        try:
            return CredentialingProgram.objects.filter(
                status='active'
            ).prefetch_related('category_rules').get(id=program_id)
        except CredentialingProgram.DoesNotExist:
            return None
    
    @staticmethod
    def get_programs_by_ids(program_ids):
        """Get multiple programs by their IDs."""
        return CredentialingProgram.objects.filter(
            id__in=program_ids,
            status='active'
        ).prefetch_related('category_rules')
    
    @staticmethod
    def get_program_categories(program):
        """Get all categories for a specific program."""
        return program.category_rules.all().order_by('sort_order', 'category_code')
    
    @staticmethod
    def get_multiple_program_categories(program_ids):
        """Get categories for multiple programs."""
        programs = ProgramService.get_programs_by_ids(program_ids)
        result = {}
        
        for program in programs:
            categories = ProgramService.get_program_categories(program)
            result[program.id] = {
                'program_name': program.name,
                'categories': categories
            }
        
        return result
    
    @staticmethod
    def validate_program_for_enrollment(program):
        """Validate that a program can be enrolled in."""
        if not program:
            return False, "Program not found"
        
        if program.status != 'active':
            return False, "Cannot enroll in a program that is not active"
        
        return True, None 