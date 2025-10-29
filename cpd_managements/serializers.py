from django.utils import timezone
from rest_framework import serializers
from .models import CredentialingProgram, Enrollment, CredentialCriteria
from .services.utils import RenewalPeriodFormatter
from .services.enrollment_service import EnrollmentService


class CredentialCriteriaSerializer(serializers.ModelSerializer):
    """
    Serializer for credentialing program criteria/rules
    """
    
    class Meta:
        model = CredentialCriteria
        fields = ['id', 'category_code', 'category_name', 'category_description', 'points_per_hour', 'sort_order']


class ProgramDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for credentialing programs including criteria and associated CPD activities
    """
    methodology_display = serializers.CharField(source='get_methodology_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    renewal_period_display = serializers.SerializerMethodField()
    category_rules = CredentialCriteriaSerializer(many=True, read_only=True)
    required_points_display = serializers.SerializerMethodField()
    required_hours_display = serializers.SerializerMethodField()
    max_carryover_points_display = serializers.SerializerMethodField()
    max_carryover_hours_display = serializers.SerializerMethodField()
    
    class Meta:
        model = CredentialingProgram
        fields = [
            'id', 'name', 'slug', 'description', 'provider', 'methodology', 'methodology_display',
            'renewal_period_months', 'renewal_period_display', 'required_points_display', 'required_hours_display', 
            'allow_carryover', 'max_carryover_points_display', 'max_carryover_hours_display', 
            'status', 'status_display', 'category_rules', 'created_at'
        ]
    
    def get_renewal_period_display(self, obj):
        """Return human-readable renewal period using service."""
        return RenewalPeriodFormatter.format_renewal_period(obj.renewal_period_months)
    
    def get_required_points_display(self, obj):
        """Return required points only if the program uses points."""
        if obj.uses_points:
            return float(obj.required_points) if obj.required_points > 0 else None
        return None
    
    def get_required_hours_display(self, obj):
        """Return required hours only if the program uses hours."""
        if obj.uses_hours:
            return float(obj.required_hours) if obj.required_hours > 0 else None
        return None
    
    def get_max_carryover_points_display(self, obj):
        """Return max carryover points only if the program uses points and allows carryover."""
        if obj.uses_points and obj.allow_carryover:
            return float(obj.max_carryover_points) if obj.max_carryover_points else None
        return None
    
    def get_max_carryover_hours_display(self, obj):
        """Return max carryover hours only if the program uses hours and allows carryover."""
        if obj.uses_hours and obj.allow_carryover:
            return float(obj.max_carryover_hours) if obj.max_carryover_hours else None
        return None


class ProgramListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing available credentialing programs
    """
    methodology_display = serializers.CharField(source='get_methodology_display', read_only=True)
    renewal_period_display = serializers.SerializerMethodField()
    required_points_display = serializers.SerializerMethodField()
    required_hours_display = serializers.SerializerMethodField()
    max_carryover_points_display = serializers.SerializerMethodField()
    max_carryover_hours_display = serializers.SerializerMethodField()
    
    class Meta:
        model = CredentialingProgram
        fields = [
            'id', 'name', 'slug', 'description', 'provider', 'methodology', 'methodology_display',
            'renewal_period_months', 'renewal_period_display', 'required_points_display', 'required_hours_display', 
            'allow_carryover', 'max_carryover_points_display', 'max_carryover_hours_display', 'status'
        ]
    
    def get_renewal_period_display(self, obj):
        """Return human-readable renewal period using service."""
        return RenewalPeriodFormatter.format_renewal_period(obj.renewal_period_months)
    
    def get_required_points_display(self, obj):
        """Return required points only if the program uses points."""
        if obj.uses_points:
            return float(obj.required_points) if obj.required_points > 0 else None
        return None
    
    def get_required_hours_display(self, obj):
        """Return required hours only if the program uses hours."""
        if obj.uses_hours:
            return float(obj.required_hours) if obj.required_hours > 0 else None
        return None
    
    def get_max_carryover_points_display(self, obj):
        """Return max carryover points only if the program uses points and allows carryover."""
        if obj.uses_points and obj.allow_carryover:
            return float(obj.max_carryover_points) if obj.max_carryover_points else None
        return None
    
    def get_max_carryover_hours_display(self, obj):
        """Return max carryover hours only if the program uses hours and allows carryover."""
        if obj.uses_hours and obj.allow_carryover:
            return float(obj.max_carryover_hours) if obj.max_carryover_hours else None
        return None


class EnrollmentSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and retrieving program enrollments
    """
    cycle_start_date = serializers.DateField(required=False)
    is_current_cycle_active = serializers.SerializerMethodField()
    program_details = serializers.SerializerMethodField()
    progress_summary = serializers.SerializerMethodField()
    accumulated_hours_display = serializers.SerializerMethodField()
    accumulated_points_display = serializers.SerializerMethodField()
    applied_carryover_hours_display = serializers.SerializerMethodField()
    applied_carryover_points_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Enrollment
        fields = [
            'id', 'user', 'program', 'program_details', 'enrollment_date', 
            'cycle_start_date', 'cycle_end_date', 'status', 'is_current_cycle_active',
            'accumulated_hours_display', 'accumulated_points_display', 'applied_carryover_hours_display', 
            'applied_carryover_points_display', 'progress_summary'
        ]
        read_only_fields = [
            'id', 'user', 'enrollment_date', 'cycle_end_date', 'status'
        ]

    def get_is_current_cycle_active(self, obj):
        """Return whether the enrollment cycle is currently active."""
        return obj.is_current_cycle_active
    
    def get_accumulated_hours_display(self, obj):
        """Return accumulated hours only if the program uses hours."""
        if obj.program.uses_hours:
            return float(obj.accumulated_hours)
        return None
    
    def get_accumulated_points_display(self, obj):
        """Return accumulated points only if the program uses points."""
        if obj.program.uses_points:
            return float(obj.accumulated_points)
        return None
    
    def get_applied_carryover_hours_display(self, obj):
        """Return carryover hours only if the program uses hours and allows carryover."""
        if obj.program.uses_hours and obj.program.allow_carryover:
            return float(obj.applied_carryover_hours)
        return None
    
    def get_applied_carryover_points_display(self, obj):
        """Return carryover points only if the program uses points and allows carryover."""
        if obj.program.uses_points and obj.program.allow_carryover:
            return float(obj.applied_carryover_points)
        return None
    
    def get_program_details(self, obj):
        """Return basic program information."""
        program_details = {
            'id': obj.program.id,
            'name': obj.program.name,
            'provider': obj.program.provider,
            'methodology': obj.program.methodology,
            'renewal_period_months': obj.program.renewal_period_months,
            'renewal_period_display': RenewalPeriodFormatter.format_renewal_period(obj.program.renewal_period_months),
        }
        
        # Only include points if the program uses points
        if obj.program.uses_points:
            program_details['required_points'] = float(obj.program.required_points) if obj.program.required_points > 0 else None
        
        # Only include hours if the program uses hours
        if obj.program.uses_hours:
            program_details['required_hours'] = float(obj.program.required_hours) if obj.program.required_hours > 0 else None
        
        return program_details
    
    def get_progress_summary(self, obj):
        """Return progress summary for this enrollment."""
        progress = {}
        
        if obj.program.uses_points:
            progress['points'] = {
                'accumulated': float(obj.accumulated_points),
                'required': float(obj.program.required_points),
                'remaining': float(obj.program.required_points - obj.accumulated_points),
                'percentage': round((float(obj.accumulated_points) / float(obj.program.required_points)) * 100, 1) if obj.program.required_points > 0 else 0
            }
        
        if obj.program.uses_hours:
            progress['hours'] = {
                'accumulated': float(obj.accumulated_hours),
                'required': float(obj.program.required_hours),
                'remaining': float(obj.program.required_hours - obj.accumulated_hours),
                'percentage': round((float(obj.accumulated_hours) / float(obj.program.required_hours)) * 100, 1) if obj.program.required_hours > 0 else 0
            }
        
        return progress

    def validate_program(self, value):
        """
        Validate that the program is active and available for enrollment.
        """
        if value.status != 'active':
            raise serializers.ValidationError("Cannot enroll in a program that is not active.")
        return value

    def validate(self, data):
        """
        Validate the enrollment data using the service layer.
        """
        user = self.context['request'].user
        program = data.get('program')
        cycle_start_date = data.get('cycle_start_date')

        # Use service layer for validation
        is_valid, error_message = EnrollmentService.validate_enrollment_creation(
            user, program, cycle_start_date
        )
        
        if not is_valid:
            raise serializers.ValidationError({'program': error_message})
        
        return data
    
    def validate_cycle_start_date(self, value):
        """
        Validate that cycle_start_date is not in the future.
        """
        if value and value > timezone.now().date():
            raise serializers.ValidationError("Enrollment cycle start date cannot be in the future.")
        return value

    def create(self, validated_data):
        """
        Create enrollment using the service layer.
        """
        request = self.context.get('request')
        user = request.user
        program = validated_data.get('program')
        cycle_start_date = validated_data.get('cycle_start_date')

        # Use service layer to create enrollment
        enrollment, error_message = EnrollmentService.create_enrollment(
            user, program, cycle_start_date
        )
        
        if error_message:
            raise serializers.ValidationError(error_message)
        
        return enrollment