from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from django.utils.safestring import mark_safe
from .models import User, Profession


@admin.register(Profession)
class ProfessionAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for Professions with comprehensive management features.
    """
    list_display = ['name', 'professional_count', 'created_info']
    search_fields = ['name']
    readonly_fields = ['id', 'professional_count']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name')
        }),
        ('Statistics', {
            'fields': ('professional_count',),
            'classes': ('collapse',)
        }),
    )
    
    def professional_count(self, obj):
        """Display count of professionals with this profession."""
        count = obj.professionals.count()
        if count == 0:
            return format_html('<span style="color: gray;">No professionals</span>')
        return format_html(
            '<a href="{}?profession__id__exact={}" style="color: green;">{} professional{}</a>',
            reverse('admin:users_user_changelist'),
            obj.id,
            count,
            's' if count != 1 else ''
        )
    professional_count.short_description = "Professionals"
    
    def created_info(self, obj):
        """Display creation info."""
        return format_html(
            '<span style="color: gray; font-size: 0.9em;">ID: {}</span>',
            obj.id
        )
    created_info.short_description = "Info"
    
    def get_queryset(self, request):
        """Optimize queryset with annotations."""
        return super().get_queryset(request).annotate(
            professional_count_annotation=Count('professionals')
        )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Enhanced admin interface for Users with role-based management and comprehensive features.
    """
    list_display = [
        'email', 'get_full_name_display', 'role', 'profession_display', 
        'is_active', 'is_onboarded', 'enrollment_count', 'created_at'
    ]
    list_filter = [
        'role', 'is_active', 'is_onboarded', 'is_staff', 'is_superuser',
        'profession', 'created_at'
    ]
    search_fields = ['email', 'first_name', 'last_name', 'organization_name']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'last_login', 'date_joined_display',
        'enrollment_count', 'cpd_log_count'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Authentication', {
            'fields': ('id', 'email', 'password')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'role')
        }),
        ('Professional Information', {
            'fields': ('profession', 'license_number'),
            'classes': ('collapse',)
        }),
        ('Organization Information', {
            'fields': (
                'organization_name', 'organization_contact_email',
                'organization_contact_phone', 'organization_address'
            ),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Status & Progress', {
            'fields': ('is_onboarded', 'enrollment_count', 'cpd_log_count'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'role'),
        }),
        ('Professional Information', {
            'fields': ('profession', 'license_number'),
            'classes': ('collapse',)
        }),
        ('Organization Information', {
            'fields': (
                'organization_name', 'organization_contact_email',
                'organization_contact_phone', 'organization_address'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'activate_users', 'deactivate_users', 'mark_as_onboarded',
        'mark_as_not_onboarded', 'send_welcome_email'
    ]
    
    def get_full_name_display(self, obj):
        """Display user's full name with fallback to email."""
        full_name = obj.get_full_name()
        if full_name.strip():
            return full_name
        return format_html('<em style="color: gray;">{}</em>', obj.email.split('@')[0])
    get_full_name_display.short_description = "Name"
    get_full_name_display.admin_order_field = 'first_name'
    
    def profession_display(self, obj):
        """Display profession information."""
        if obj.role != 'professional':
            return format_html('<span style="color: gray;">N/A ({})</span>', obj.get_role_display())
        
        if obj.profession:
            return format_html(
                '<a href="{}" title="View profession details">{}</a>',
                reverse('admin:users_profession_change', args=[obj.profession.pk]),
                obj.profession.name
            )
        return format_html('<span style="color: orange;">Not set</span>')
    profession_display.short_description = "Profession"
    
    def enrollment_count(self, obj):
        """Display count of program enrollments."""
        if obj.role != 'professional':
            return format_html('<span style="color: gray;">N/A</span>')
        
        try:
            count = obj.program_enrollments.count()
            if count == 0:
                return format_html('<span style="color: gray;">No enrollments</span>')
            return format_html(
                '<a href="{}?user__id__exact={}" style="color: green;">{} enrollment{}</a>',
                reverse('admin:cpd_managements_enrollment_changelist'),
                obj.id,
                count,
                's' if count != 1 else ''
            )
        except:
            return format_html('<span style="color: gray;">N/A</span>')
    enrollment_count.short_description = "Enrollments"
    
    def cpd_log_count(self, obj):
        """Display count of CPD log entries."""
        if obj.role != 'professional':
            return format_html('<span style="color: gray;">N/A</span>')
        
        try:
            count = obj.cpd_log_entries.count()
            if count == 0:
                return format_html('<span style="color: gray;">No logs</span>')
            return format_html(
                '<a href="{}?user__id__exact={}" style="color: blue;">{} log{}</a>',
                reverse('admin:cpd_tracking_cpdlogentry_changelist'),
                obj.id,
                count,
                's' if count != 1 else ''
            )
        except:
            return format_html('<span style="color: gray;">N/A</span>')
    cpd_log_count.short_description = "CPD Logs"
    
    def date_joined_display(self, obj):
        """Display formatted creation date."""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    date_joined_display.short_description = "Date Joined"
    
    def activate_users(self, request, queryset):
        """Bulk activate selected users."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} users activated successfully.")
    activate_users.short_description = "Activate selected users"
    
    def deactivate_users(self, request, queryset):
        """Bulk deactivate selected users."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} users deactivated.")
    deactivate_users.short_description = "Deactivate selected users"
    
    def mark_as_onboarded(self, request, queryset):
        """Mark selected users as onboarded."""
        updated = queryset.update(is_onboarded=True)
        self.message_user(request, f"{updated} users marked as onboarded.")
    mark_as_onboarded.short_description = "Mark as onboarded"
    
    def mark_as_not_onboarded(self, request, queryset):
        """Mark selected users as not onboarded."""
        updated = queryset.update(is_onboarded=False)
        self.message_user(request, f"{updated} users marked as not onboarded.")
    mark_as_not_onboarded.short_description = "Mark as not onboarded"
    
    def send_welcome_email(self, request, queryset):
        """Send welcome email to selected users."""
        count = 0
        for user in queryset:
            if user.is_active and user.email:
                # Here you would implement your email sending logic
                # For now, we'll just count the users
                count += 1
        
        if count > 0:
            self.message_user(request, f"Welcome emails would be sent to {count} users.")
        else:
            self.message_user(request, "No eligible users found for welcome emails.", level='WARNING')
    send_welcome_email.short_description = "Send welcome email"
    
    def get_queryset(self, request):
        """Optimize queryset with select_related and annotations."""
        return super().get_queryset(request).select_related('profession').annotate(
            enrollment_count_annotation=Count('program_enrollments', distinct=True),
            cpd_log_count_annotation=Count('cpd_log_entries', distinct=True)
        )
    
    def get_fieldsets(self, request, obj=None):
        """Customize fieldsets based on user role."""
        if not obj:
            return self.add_fieldsets
        
        # Base fieldsets
        fieldsets = list(self.fieldsets)
        
        # Hide professional fields for non-professionals
        if obj.role != 'professional':
            fieldsets = [fs for fs in fieldsets if fs[0] != 'Professional Information']
        
        # Hide organization fields for non-organizations
        if obj.role != 'organization':
            fieldsets = [fs for fs in fieldsets if fs[0] != 'Organization Information']
        
        return fieldsets
    
    def get_readonly_fields(self, request, obj=None):
        """Customize readonly fields based on context."""
        readonly_fields = list(self.readonly_fields)
        
        # Make email readonly for existing users (except superusers)
        if obj and not request.user.is_superuser:
            readonly_fields.append('email')
        
        return readonly_fields