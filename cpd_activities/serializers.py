from rest_framework import serializers
from django.utils import timezone
from .models import CPDActivity
from users.models import Profession


class CPDActivityListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing approved CPD activities for selection by users.
    """
    recommended_profession_names = serializers.SerializerMethodField()
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_created_by_provider = serializers.SerializerMethodField()
    
    class Meta:
        model = CPDActivity
        fields = [
            'id', 'title', 'slug', 'description', 'thumbnail', 'link', 
            'provider', 'activity_type', 'activity_type_display', 
            'start_datetime', 'end_datetime', 'default_points_per_hour',
            'status', 'status_display', 'recommended_profession_names',
            'is_created_by_provider', 'created_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at']
    
    def get_recommended_profession_names(self, obj):
        """Return list of recommended profession names."""
        return [profession.name for profession in obj.recommended_professions.all()]

    def get_is_created_by_provider(self, obj):
        """Check if the activity was created by the current provider."""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            if request.user.role == 'provider' and obj.created_by == request.user:
                return True
        return False


class CPDActivityDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for CPD activity including all relationships.
    """
    recommended_professions = serializers.SerializerMethodField()
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    recommended_profession_names = serializers.SerializerMethodField()
    is_created_by_provider = serializers.SerializerMethodField()
    
    class Meta:
        model = CPDActivity
        fields = [
            'id', 'title', 'slug', 'description', 'thumbnail', 'link', 
            'provider', 'activity_type', 'activity_type_display', 
            'start_datetime', 'end_datetime', 'default_points_per_hour',
            'recommended_professions', 'status', 'status_display', 
            'recommended_profession_names', 'is_created_by_provider',
            'is_manual', 'created_by', 'approved_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'approved_at', 'updated_at']
    
    def get_recommended_professions(self, obj):
        """Return detailed profession information."""
        return [{
            'id': profession.id,
            'name': profession.name
        } for profession in obj.recommended_professions.all()]
    
    def get_recommended_profession_names(self, obj):
        """Return list of recommended profession names."""
        return [profession.name for profession in obj.recommended_professions.all()]

    def get_is_created_by_provider(self, obj):
        """Check if the activity was created by the current provider."""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            if request.user.role == 'provider' and obj.created_by == request.user:
                return True
        return False


class CreateManualCPDActivitySerializer(serializers.ModelSerializer):
    """
    Serializer for creating manual CPD activities by professionals.
    These are self-reported activities that need approval.
    """
    
    class Meta:
        model = CPDActivity
        fields = [
            'title', 'description', 'provider', 'activity_type',
            'start_datetime', 'end_datetime', 'default_points_per_hour',
            'link'
        ]
    
    def create(self, validated_data):
        request = self.context['request']
        
        # Set manual activity specific fields
        validated_data['is_manual'] = True
        validated_data['created_by'] = request.user
        validated_data['status'] = 'pending'  # Manual activities need approval
        
        activity = CPDActivity.objects.create(**validated_data)
        
        return activity
    
    def validate_start_datetime(self, value):
        """Validate start datetime for manual activities."""
        if value and value > timezone.now():
            raise serializers.ValidationError("Manual activities cannot have future start dates.")
        if value and value < timezone.now() - timezone.timedelta(days=365):
            raise serializers.ValidationError("Manual activities cannot be older than 1 year.")
        return value
    
    def validate(self, data):
        """Cross-field validation for manual activities."""
        start_datetime = data.get('start_datetime')
        end_datetime = data.get('end_datetime')
        
        if start_datetime and end_datetime and end_datetime <= start_datetime:
            raise serializers.ValidationError({
                'end_datetime': 'End datetime must be after start datetime.'
            })
        
        # For manual activities, both start and end dates are usually required
        if not start_datetime:
            raise serializers.ValidationError({
                'start_datetime': 'Start datetime is required for manual activities.'
            })
        
        return data


class CreateProviderCPDActivitySerializer(serializers.ModelSerializer):
    """
    Serializer for creating CPD activities by providers.
    Provider activities are catalog items that professionals can enroll in.
    """
    recommended_professions = serializers.PrimaryKeyRelatedField(
        queryset=Profession.objects.all(),
        many=True,
        required=False,
        help_text="Professions for which this activity is recommended"
    )
    
    class Meta:
        model = CPDActivity
        fields = [
            'title', 'description', 'provider', 'activity_type',
            'start_datetime', 'end_datetime', 'default_points_per_hour',
            'recommended_professions', 'link'
        ]
    
    def create(self, validated_data):
        request = self.context['request']
        recommended_professions = validated_data.pop('recommended_professions', [])
        
        # Set provider-specific fields
        validated_data['is_manual'] = False  # Provider activities are catalog items
        validated_data['status'] = 'pending'  # Needs approval
        validated_data['created_by'] = request.user
        
        # Create the activity
        activity = CPDActivity.objects.create(**validated_data)
        
        # Assign relationships
        if recommended_professions:
            activity.recommended_professions.set(recommended_professions)
        
        return activity
    
    def validate_start_datetime(self, value):
        """Validate start datetime for provider activities."""
        if value and value > timezone.now() + timezone.timedelta(days=730):  # 2 years
            raise serializers.ValidationError("Start date cannot be more than 2 years in the future.")
        return value
    
    def validate_end_datetime(self, value):
        """Validate end datetime is after start datetime."""
        # Use a simpler validation approach
        if value and hasattr(self, 'initial_data'):
            start_datetime_str = self.initial_data.get('start_datetime')
            if start_datetime_str:
                from django.utils.dateparse import parse_datetime
                start_datetime = parse_datetime(start_datetime_str)
                if start_datetime and value <= start_datetime:
                    raise serializers.ValidationError("End datetime must be after start datetime.")
        return value
    
    def validate(self, data):
        """Cross-field validation."""
        start_datetime = data.get('start_datetime')
        end_datetime = data.get('end_datetime')
        
        if start_datetime and end_datetime and end_datetime <= start_datetime:
            raise serializers.ValidationError({
                'end_datetime': 'End datetime must be after start datetime.'
            })
        
        return data
