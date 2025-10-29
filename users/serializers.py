from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, Profession

class OnboardingSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, required=True)

    # Professional fields
    profession = serializers.PrimaryKeyRelatedField(
        queryset=Profession.objects.all(), 
        required=False, 
        allow_null=True
    )
    license_number = serializers.CharField(max_length=100, required=False)

    def validate(self, data):
        role = data.get('role')
        if role == 'professional':
            if not data.get('profession'):
                raise serializers.ValidationError({"profession": "This field is required for professionals."})
        return data

class UserProfileSerializer(serializers.ModelSerializer):
    profession_name = serializers.CharField(source='profession.name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role',
            'is_onboarded',
            # Professional profile fields
            'profession', 'profession_name', 'license_number', 
        ]
        read_only_fields = ['id', 'email', 'date_joined']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        if instance.role == 'provider' or instance.role == 'admin':
            # For provider and admin, remove professional specific fields
            data.pop('profession', None)
            data.pop('profession_name', None)
            data.pop('license_number', None)
        
        return data

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['email'] = user.email
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        return token