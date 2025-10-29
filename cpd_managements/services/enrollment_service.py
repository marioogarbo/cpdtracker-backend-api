from django.utils import timezone
from datetime import timedelta
from calendar import monthrange
from decimal import Decimal
from ..models import Enrollment


class EnrollmentService:
    """Service class for enrollment-related operations."""
    
    @staticmethod
    def get_user_enrollments(user, status_filter=None):
        """Get enrollments for a user with optional status filtering."""
        queryset = Enrollment.objects.filter(user=user).select_related('program')
        
        if status_filter:
            if isinstance(status_filter, list):
                queryset = queryset.filter(status__in=status_filter)
            else:
                queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-enrollment_date')
    
    @staticmethod
    def get_user_active_enrollments(user):
        """Get all active enrollments for a user."""
        return EnrollmentService.get_user_enrollments(user, status='active')
    
    @staticmethod
    def get_user_archived_enrollments(user):
        """Get all archived enrollments for a user."""
        return EnrollmentService.get_user_enrollments(user, status='archived')
    
    @staticmethod
    def get_user_all_enrollments(user):
        """Get all enrollments (active, completed, archived) for a user."""
        return EnrollmentService.get_user_enrollments(
            user, 
            status_filter=['active', 'completed', 'archived']
        )
    
    @staticmethod
    def get_enrollment_by_id(user, enrollment_id):
        """Get a specific enrollment for a user."""
        try:
            return Enrollment.objects.filter(
                user=user
            ).select_related('program').get(id=enrollment_id)
        except Enrollment.DoesNotExist:
            return None
    
    @staticmethod
    def validate_enrollment_creation(user, program, cycle_start_date=None):
        """
        Validate if a user can enroll in a program.
        Returns (is_valid, error_message)
        """
        # Check for existing active enrollment
        active_enrollments = Enrollment.objects.filter(
            user=user,
            program=program,
            status='active'
        )
        
        if active_enrollments.exists():
            existing = active_enrollments.first()
            return False, (
                f"You already have an active enrollment in {program.name} "
                f"(cycle: {existing.cycle_start_date} to {existing.cycle_end_date}). "
                f"Please complete or cancel your existing enrollment before creating a new one."
            )
        
        # Check for archived enrollment
        archived_enrollments = Enrollment.objects.filter(
            user=user,
            program=program,
            status='archived'
        )
        
        if archived_enrollments.exists():
            existing = archived_enrollments.first()
            return False, (
                f"You have an archived enrollment in {program.name} "
                f"(cycle: {existing.cycle_start_date} to {existing.cycle_end_date}). "
                f"You must delete the archived enrollment before creating a new one."
            )
        
        # Validate cycle start date
        if cycle_start_date and cycle_start_date > timezone.now().date():
            return False, "Enrollment cycle start date cannot be in the future."
        
        # Check for reasonable number of enrollments
        total_enrollments = Enrollment.objects.filter(
            user=user,
            program=program
        ).count()
        
        if total_enrollments >= 50:
            return False, f"Too many enrollments found for {program.name}. Please contact support."
        
        return True, None
    
    @staticmethod
    def calculate_cycle_end_date(cycle_start_date, renewal_months):
        """
        Calculate the cycle end date based on start date and renewal period.
        """
        # Calculate end date by adding months safely
        year = cycle_start_date.year
        month = cycle_start_date.month + renewal_months
        day = cycle_start_date.day
        
        # Adjust year and month if month > 12
        while month > 12:
            year += 1
            month -= 12
        
        # Handle day overflow (e.g., Jan 31 + 1 month = Feb 28/29, not Feb 31)
        max_day_in_month = monthrange(year, month)[1]
        if day > max_day_in_month:
            day = max_day_in_month
        
        try:
            cycle_end_date = cycle_start_date.replace(year=year, month=month, day=day)
        except ValueError:
            # Fallback for any remaining edge cases
            cycle_end_date = cycle_start_date.replace(year=year, month=month, day=1)
        
        # Subtract one day to make it inclusive
        cycle_end_date = cycle_end_date - timedelta(days=1)
        
        return cycle_end_date
    
    @staticmethod
    def create_enrollment(user, program, cycle_start_date=None):
        """
        Create a new enrollment for a user in a program.
        Returns (enrollment, error_message)
        """
        # Validate enrollment creation
        is_valid, error_message = EnrollmentService.validate_enrollment_creation(
            user, program, cycle_start_date
        )
        
        if not is_valid:
            return None, error_message
        
        # Use provided cycle_start_date or default to today
        if not cycle_start_date:
            cycle_start_date = timezone.now().date()
        
        # Calculate cycle end date
        cycle_end_date = EnrollmentService.calculate_cycle_end_date(
            cycle_start_date, 
            program.renewal_period_months
        )
        
        try:
            enrollment = Enrollment.objects.create(
                user=user,
                program=program,
                cycle_start_date=cycle_start_date,
                cycle_end_date=cycle_end_date,
                status='active'
            )
            return enrollment, None
        except Exception as e:
            if 'unique constraint' in str(e).lower():
                return None, (
                    f"An enrollment for {program.name} starting on {cycle_start_date} already exists. "
                    "Please choose a different start date."
                )
            else:
                return None, f"Failed to create enrollment: {str(e)}"
    
    @staticmethod
    def update_enrollment_status(enrollment, new_status):
        """
        Update enrollment status with validation.
        Returns (success, message)
        """
        allowed_statuses = ['completed', 'cancelled', 'active']
        
        if new_status not in allowed_statuses:
            return False, f"Invalid status. Allowed values: {', '.join(allowed_statuses)}"
        
        enrollment.status = new_status
        enrollment.save()
        
        action_map = {
            'completed': 'completed',
            'cancelled': 'cancelled',
            'active': 'reactivated'
        }
        
        return True, f"Successfully {action_map[new_status]} enrollment in {enrollment.program.name}"
    
    @staticmethod
    def delete_enrollment(enrollment):
        """
        Soft delete an enrollment (mark as deleted).
        Returns (success, message)
        """
        if enrollment.status == 'deleted':
            return False, "Enrollment is already deleted"
        
        enrollment.status = 'deleted'
        enrollment.save()
        
        return True, (
            f"Successfully deleted enrollment in {enrollment.program.name}. "
            "You can re-enroll in this program anytime."
        )
    
    @staticmethod
    def archive_enrollment(enrollment):
        """
        Archive an enrollment (hide from user but prevent re-enrollment).
        Returns (success, message)
        """
        if enrollment.status == 'archived':
            return False, "Enrollment is already archived"
        
        if enrollment.status == 'deleted':
            return False, "Cannot archive a deleted enrollment"
        
        enrollment.status = 'archived'
        enrollment.save()
        
        return True, (
            f"Successfully archived enrollment in {enrollment.program.name}. "
            "You must delete it to re-enroll."
        )
    
    @staticmethod
    def reactivate_enrollment(enrollment):
        """
        Reactivate an archived enrollment.
        Returns (success, message)
        """
        if enrollment.status != 'archived':
            return False, "Only archived enrollments can be reactivated"
        
        # Check if there's already an active enrollment in this program
        existing_active = Enrollment.objects.filter(
            user=enrollment.user,
            program=enrollment.program,
            status='active'
        ).exclude(pk=enrollment.pk)
        
        if existing_active.exists():
            return False, (
                f"You already have an active enrollment in {enrollment.program.name}. "
                "Please delete the active enrollment first."
            )
        
        enrollment.status = 'active'
        enrollment.save()
        
        return True, f"Successfully reactivated enrollment in {enrollment.program.name}"
    
    @staticmethod
    def update_cycle_start_date(enrollment, new_cycle_start_date):
        """
        Update enrollment cycle start date and recalculate end date.
        Returns (success, message)
        """
        try:
            # Validate the new start date
            from datetime import datetime
            new_start_date = datetime.strptime(new_cycle_start_date, '%Y-%m-%d').date()
            
            # Check if the new start date is in the future
            if new_start_date > timezone.now().date():
                return False, "Cycle start date cannot be in the future"
            
            # Check if there's already an enrollment with this start date for the same program
            existing_enrollment = Enrollment.objects.filter(
                user=enrollment.user,
                program=enrollment.program,
                cycle_start_date=new_start_date
            ).exclude(pk=enrollment.pk)
            
            if existing_enrollment.exists():
                return False, (
                    f"You already have an enrollment in {enrollment.program.name} "
                    f"with start date {new_start_date}"
                )
            
            # Update the cycle start date
            old_start_date = enrollment.cycle_start_date
            enrollment.cycle_start_date = new_start_date
            
            # Recalculate cycle end date
            enrollment.cycle_end_date = EnrollmentService.calculate_cycle_end_date(
                new_start_date, 
                enrollment.program.renewal_period_months
            )
            
            enrollment.save()
            
            return True, (
                f"Successfully updated cycle start date for {enrollment.program.name} "
                f"from {old_start_date} to {new_start_date}"
            )
            
        except ValueError:
            return False, "Invalid date format. Use YYYY-MM-DD format"
        except Exception as e:
            return False, f"Failed to update enrollment: {str(e)}" 