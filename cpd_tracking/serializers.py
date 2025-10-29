from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from .models import CPDLogEntry, CPDLogDetails, Evidence
from cpd_activities.models import CPDActivity
from cpd_managements.models import Enrollment


class EvidenceSerializer(serializers.ModelSerializer):
    """
    Serializer for CPD evidence files/links
    """
    class Meta:
        model = Evidence
        fields = ['id', 'type', 'file', 'url', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

    def validate(self, data):
        """Ensure either file or url is provided, but not both"""
        if data.get('type') == 'file' and not data.get('file'):
            raise serializers.ValidationError("File is required when type is 'file'")
        if data.get('type') == 'url' and not data.get('url'):
            raise serializers.ValidationError("URL is required when type is 'url'")
        if data.get('file') and data.get('url'):
            raise serializers.ValidationError("Provide either file or URL, not both")
        return data


class CPDLogEntryListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing CPD log entries
    """
    activity_title = serializers.SerializerMethodField()
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    
    class Meta:
        model = CPDLogEntry
        fields = [
            'id', 'is_manual', 'activity_type', 'activity_type_display', 'activity_title',
            'hours_spent', 'completed_at', 'created_at'
        ]

    def get_activity_title(self, obj):
        """Get activity title from catalog activity or use a default for manual entries"""
        if obj.cpd_activity:
            return obj.cpd_activity.title
        return f"Manual Activity - {obj.completed_at}"


class CPDLogDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for CPD log details showing program-specific information
    """
    enrollment_info = serializers.SerializerMethodField()
    applied_criteria_info = serializers.SerializerMethodField()
    total_points = serializers.SerializerMethodField()
    total_hours = serializers.SerializerMethodField()
    points_per_hour = serializers.SerializerMethodField()
    
    class Meta:
        model = CPDLogDetails
        fields = [
            'id', 'enrollment_info', 'applied_criteria_info', 'program_category_code',
            'points_per_hour', 'total_points', 'total_hours',
            'validated_at', 'created_at'
        ]
    
    def get_total_points(self, obj):
        """Return total_points as a float"""
        return float(obj.total_points)
    
    def get_total_hours(self, obj):
        """Return total_hours as a float"""
        return float(obj.total_hours)
    
    def get_points_per_hour(self, obj):
        """Return points_per_hour as a float"""
        return float(obj.points_per_hour)
    
    def get_enrollment_info(self, obj):
        """Get program enrollment information including status"""
        return {
            'id': obj.enrollment.id,
            'program_id': obj.enrollment.program.id,
            'program_name': obj.enrollment.program.name,
            'program_provider': obj.enrollment.program.provider,
            'methodology': obj.enrollment.program.methodology,
            'cycle_start_date': obj.enrollment.cycle_start_date,
            'cycle_end_date': obj.enrollment.cycle_end_date,
            'status': obj.enrollment.status,
            'is_current_cycle_active': obj.enrollment.is_current_cycle_active,
        }
    
    def get_applied_criteria_info(self, obj):
        """Return details about the applied criteria/category"""
        if obj.applied_criteria:
            return {
                'id': obj.applied_criteria.id,
                'category_name': obj.applied_criteria.category_name,
                'category_code': obj.applied_criteria.category_code,
                'points_per_hour': float(obj.applied_criteria.points_per_hour),
                'description': obj.applied_criteria.category_description or '',
            }
        return None


class CPDLogbookEntrySerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for CPD logbook entries showing all program-specific details
    """
    activity_details = serializers.SerializerMethodField()
    program_details = CPDLogDetailSerializer(source='log_details', many=True, read_only=True)
    evidences = EvidenceSerializer(many=True, read_only=True)
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    total_points_earned = serializers.SerializerMethodField()
    hours_spent = serializers.SerializerMethodField()
    
    class Meta:
        model = CPDLogEntry
        fields = [
            'id', 'is_manual', 'activity_type', 'activity_type_display',
            'hours_spent', 'completed_at', 'start_datetime', 'end_datetime',
            'notes', 'activity_details', 'program_details', 'evidences',
            'total_points_earned', 'created_at', 'updated_at'
        ]

    def get_hours_spent(self, obj):
        """Return hours_spent as a float"""
        return float(obj.hours_spent)

    def get_activity_details(self, obj):
        """Return comprehensive activity details"""
        if obj.cpd_activity:
            return {
                'id': obj.cpd_activity.id,
                'title': obj.cpd_activity.title,
                'description': obj.cpd_activity.description or '',
                'provider': obj.cpd_activity.provider,
                'activity_type': obj.cpd_activity.activity_type,
                'default_points_per_hour': float(obj.cpd_activity.default_points_per_hour or 0),
                'is_manual': obj.cpd_activity.is_manual,
                'status': obj.cpd_activity.status,
            }
        else:
            # For manual entries, use the manual fields from the log entry
            return {
                'id': None,
                'title': obj.manual_title or f"Manual Entry - {obj.get_activity_type_display()}",
                'description': obj.manual_description or '',
                'provider': obj.manual_provider or '',
                'activity_type': obj.activity_type,
                'default_points_per_hour': 1.0,
                'is_manual': True,
                'status': 'approved',
            }
    
    def get_total_points_earned(self, obj):
        """Calculate total points earned across all program assignments"""
        total = sum(float(detail.total_points) for detail in obj.log_details.all())
        return total


class CPDLogEntrySerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for creating and retrieving CPD log entries
    """
    evidences = EvidenceSerializer(many=True, read_only=True)
    activity_details = serializers.SerializerMethodField()
    enrollment_details = serializers.SerializerMethodField()
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    
    # Fields for manual activity creation
    title = serializers.CharField(write_only=True, required=False)
    description = serializers.CharField(write_only=True, required=False)
    provider = serializers.CharField(write_only=True, required=False)
    
    # Frontend compatibility: accept 'category' and map to activity_type
    category = serializers.CharField(write_only=True, required=False, help_text="Frontend field that maps to activity_type")
    
    # Program enrollment selection with categories
    program_enrollment_ids = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=True,
        help_text="List of enrollment IDs to assign this activity to"
    )
    
    # Program-specific category selections (supports both new ID-based and legacy code-based)
    program_categories = serializers.DictField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text="Mapping of enrollment_id to selected category_id (preferred) or category_code (legacy). Use category IDs when possible for better data integrity."
    )
    
    class Meta:
        model = CPDLogEntry
        fields = [
            'id', 'user', 'cpd_activity', 'is_manual', 'activity_type', 'activity_type_display',
            'hours_spent', 'completed_at', 'start_datetime', 'end_datetime',
            'notes', 'activity_details', 'enrollment_details', 'evidences',
            'manual_title', 'manual_description', 'manual_provider',
            'title', 'description', 'provider', 'program_enrollment_ids', 'program_categories', 'category',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'created_at', 'updated_at'
        ]

    def get_activity_details(self, obj):
        """Return activity details for both catalog and manual entries"""
        if obj.cpd_activity:
            # For catalog activities, return activity details from CPDActivity
            return {
                'id': obj.cpd_activity.id,
                'title': obj.cpd_activity.title,
                'description': getattr(obj.cpd_activity, 'description', ''),  # Add description if available
                'provider': obj.cpd_activity.provider,
                'activity_type': obj.cpd_activity.activity_type,
                'default_points_per_hour': float(obj.cpd_activity.default_points_per_hour)
            }
        else:
            # For manual entries, return details from the log entry itself
            return {
                'id': None,
                'title': obj.manual_title or obj.title,
                'description': obj.manual_description or '',
                'provider': obj.manual_provider or '',
                'activity_type': obj.activity_type,
                'default_points_per_hour': 1.0  # Default for manual entries
            }

    def get_enrollment_details(self, obj):
        """Return related enrollment details from CPDLogDetails"""
        log_details = obj.log_details.all()
        if log_details:
            details = []
            for detail in log_details:
                details.append({
                    'enrollment_id': detail.enrollment.id,
                    'program_name': detail.enrollment.program.name,
                    'total_hours': float(detail.total_hours),
                    'total_points': float(detail.total_points),
                    'program_category_code': detail.program_category_code,
                    'applied_criteria': {
                        'category_name': detail.applied_criteria.category_name,
                        'points_per_hour': float(detail.applied_criteria.points_per_hour)
                    } if detail.applied_criteria else None
                })
            return details
        return []

    def validate(self, data):
        """Validate log entry data"""
        cpd_activity = data.get('cpd_activity')
        program_enrollment_ids = data.get('program_enrollment_ids', [])
        program_categories = data.get('program_categories', {})
        category = data.get('category')  # Frontend sends this for backward compatibility
        
        # Map category to activity_type for backend consistency
        if category:
            data['activity_type'] = category
        
        # Ensure at least one enrollment is selected
        if not program_enrollment_ids:
            raise serializers.ValidationError("At least one program enrollment must be selected")
        
        # Validate that enrollments belong to the user
        request = self.context['request']
        user_enrollments = Enrollment.objects.filter(
            id__in=program_enrollment_ids,
            user=request.user,
            status='active'
        )
        
        if len(user_enrollments) != len(program_enrollment_ids):
            raise serializers.ValidationError("One or more enrollment IDs are invalid or inactive")
        
        # Validate program categories if provided
        if program_categories:
            for enrollment_id, category_value in program_categories.items():
                if enrollment_id not in program_enrollment_ids:
                    raise serializers.ValidationError(f"Category specified for enrollment {enrollment_id} not in selected enrollments")
                
                # Validate that the category exists for the program
                enrollment = user_enrollments.filter(id=enrollment_id).first()
                if enrollment:
                    from cpd_managements.models import CredentialCriteria
                    
                    # Try to find criteria by ID first (new approach), then by code (legacy)
                    criteria = None
                    if category_value.startswith('rule_'):  # Looks like an ID
                        criteria = CredentialCriteria.objects.filter(
                            id=category_value,
                            program=enrollment.program
                        ).first()
                    
                    if not criteria:  # Fall back to code-based lookup
                        criteria = CredentialCriteria.objects.filter(
                            program=enrollment.program,
                            category_code=category_value
                        ).first()
                    
                    if not criteria:
                        raise serializers.ValidationError(
                            f"Category '{category_value}' does not exist for program '{enrollment.program.name}'"
                        )
        
        # Determine if manual and validate required fields
        if cpd_activity:
            data['is_manual'] = False
            # For catalog activities, get activity_type from the linked CPDActivity
            data['activity_type'] = cpd_activity.activity_type
        else:
            data['is_manual'] = True
            # For manual entries, title and activity_type are required
            if not data.get('title'):
                raise serializers.ValidationError("Title is required for manual entries")
            if not data.get('activity_type'):
                data['activity_type'] = 'other'  # Default fallback

        # Validate completion date - cannot be in the future
        completed_at = data.get('completed_at')
        if completed_at:
            from django.utils import timezone
            today = timezone.now().date()
            
            # Parse the date if it's a string
            if isinstance(completed_at, str):
                try:
                    from django.utils.dateparse import parse_date
                    completed_at = parse_date(completed_at)
                except (ValueError, TypeError):
                    raise serializers.ValidationError("Invalid completion date format")
            
            if completed_at and completed_at > today:
                raise serializers.ValidationError("Completion date cannot be in the future")
        
        # Clean datetime fields - convert empty strings to None
        if 'start_datetime' in data and (not data['start_datetime'] or str(data['start_datetime']).strip() == ''):
            data['start_datetime'] = None
        if 'end_datetime' in data and (not data['end_datetime'] or str(data['end_datetime']).strip() == ''):
            data['end_datetime'] = None
        
        # Validate datetime consistency - only validate if both have actual datetime values
        start_datetime = data.get('start_datetime')
        end_datetime = data.get('end_datetime')
        
        # Only validate if both fields have non-None values
        if start_datetime is not None and end_datetime is not None:
            try:
                from django.utils.dateparse import parse_datetime
                start_dt = parse_datetime(str(start_datetime)) if isinstance(start_datetime, str) else start_datetime
                end_dt = parse_datetime(str(end_datetime)) if isinstance(end_datetime, str) else end_datetime
                
                if start_dt and end_dt and end_dt <= start_dt:
                    raise serializers.ValidationError("End datetime must be after start datetime")
            except (ValueError, TypeError):
                # If parsing fails, let Django's model validation handle it
                pass
        
        return data

    @transaction.atomic
    def create(self, validated_data):
        """Create log entry with manual entry fields stored in the model"""
        request = self.context['request']
        user = request.user
        
        # Extract fields for processing
        program_enrollment_ids = validated_data.pop('program_enrollment_ids')
        program_categories = validated_data.pop('program_categories', {})
        title = validated_data.pop('title', None)
        description = validated_data.pop('description', None)
        provider = validated_data.pop('provider', None)
        # Remove category from validated_data since it's not a model field
        validated_data.pop('category', None)
        
        # Set manual entry fields if this is a manual entry
        if validated_data.get('is_manual', True):
            validated_data['manual_title'] = title
            validated_data['manual_description'] = description
            validated_data['manual_provider'] = provider
        
        validated_data['user'] = user
        
        log_entry = CPDLogEntry.objects.create(**validated_data)
        
        # Create CPDLogDetails for specified enrollments with program-specific categories
        self._create_log_details(log_entry, program_enrollment_ids, program_categories)
        
        return log_entry

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update an existing CPD log entry with manual entry fields"""
        # Extract fields for processing
        program_enrollment_ids = validated_data.pop('program_enrollment_ids', None)
        program_categories = validated_data.pop('program_categories', {})
        title = validated_data.pop('title', None)
        description = validated_data.pop('description', None)
        provider = validated_data.pop('provider', None)
        # Remove category from validated_data since it's not a model field
        validated_data.pop('category', None)
        
        # Update manual entry fields if this is a manual entry
        if instance.is_manual:
            if title is not None:
                validated_data['manual_title'] = title
            if description is not None:
                validated_data['manual_description'] = description
            if provider is not None:
                validated_data['manual_provider'] = provider
        
        # Update the instance with validated data
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update program assignments if provided
        if program_enrollment_ids is not None:
            # Delete existing log details
            instance.log_details.all().delete()
            # Create new log details
            self._create_log_details(instance, program_enrollment_ids, program_categories)
        
        return instance

    def _create_log_details(self, log_entry, enrollment_ids, program_categories=None):
        """Create CPDLogDetails for specified enrollments with program-specific categories"""
        from cpd_tracking.models import CPDLogDetails
        from cpd_managements.models import CredentialCriteria
        
        enrollments = Enrollment.objects.filter(
            id__in=enrollment_ids,
            user=log_entry.user,
            status='active'
        )
        
        for enrollment in enrollments:
            # Get program-specific category for this enrollment
            applied_criteria = None
            program_category_code = None
            
            if program_categories and enrollment.id in program_categories:
                category_value = program_categories[enrollment.id]
                
                # Try to find criteria by ID first (new approach), then by code (legacy)
                if category_value.startswith('rule_'):  # Looks like an ID
                    applied_criteria = CredentialCriteria.objects.filter(
                        id=category_value,
                        program=enrollment.program
                    ).first()
                
                if not applied_criteria:  # Fall back to code-based lookup
                    applied_criteria = CredentialCriteria.objects.filter(
                        program=enrollment.program,
                        category_code=category_value
                    ).first()
                    
                # Store the code for legacy compatibility
                if applied_criteria:
                    program_category_code = applied_criteria.category_code
                else:
                    # If no criteria found, store the value as code (legacy behavior)
                    program_category_code = category_value
            
            detail = CPDLogDetails.objects.create(
                log_entry=log_entry,
                enrollment=enrollment,
                applied_criteria=applied_criteria,
                program_category_code=program_category_code
            )
            # This will trigger the calculate_points method automatically via the save() method
            detail.save()