from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from .models import CPDActivity


@admin.register(CPDActivity)
class CPDActivityAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for CPD Activities with comprehensive functionality.
    """
    list_display = [
        'title', 'provider', 'activity_type', 'status', 'default_points_per_hour',
        'start_datetime', 'is_manual', 'log_entries_count', 'created_at'
    ]
    list_filter = [
        'status', 'activity_type', 'is_manual', 'created_at', 
        'start_datetime', 'recommended_professions'
    ]
    search_fields = ['title', 'provider', 'description']
    readonly_fields = [
        'id', 'slug', 'created_at', 'updated_at', 'created_by', 'approved_at',
        'log_entries_count'
    ]
    filter_horizontal = ['recommended_professions']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'title', 'slug', 'description', 'thumbnail')
        }),
        ('Activity Details', {
            'fields': (
                'provider', 'activity_type', 'default_points_per_hour', 
                'link', 'start_datetime', 'end_datetime'
            )
        }),
        ('Profession Assignment', {
            'fields': ('recommended_professions',),
            'classes': ('collapse',)
        }),
        ('Status & Approval', {
            'fields': ('status', 'is_manual', 'approved_at')
        }),
        ('Statistics', {
            'fields': ('log_entries_count',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'approve_activities', 'reject_activities', 'mark_as_manual',
        'mark_as_catalog', 'duplicate_activities'
    ]
    
    def log_entries_count(self, obj):
        """Display count of log entries using this activity."""
        count = obj.log_entries.count()
        if count == 0:
            return format_html('<span style="color: gray;">None</span>')
        return format_html(
            '<a href="{}?cpd_activity__id__exact={}" style="color: blue;" title="View log entries">'
            '{} log entr{}</a>',
            reverse('admin:cpd_tracking_cpdlogentry_changelist'),
            obj.id,
            count,
            'ies' if count != 1 else 'y'
        )
    log_entries_count.short_description = "Log Entries"
    
    def approve_activities(self, request, queryset):
        """Bulk approve selected activities."""
        from django.utils import timezone
        updated = queryset.update(status='approved', approved_at=timezone.now())
        self.message_user(request, f"{updated} activities approved successfully.")
    approve_activities.short_description = "✓ Approve selected activities"
    
    def reject_activities(self, request, queryset):
        """Bulk reject selected activities."""
        updated = queryset.update(status='rejected', approved_at=None)
        self.message_user(request, f"{updated} activities rejected.")
    reject_activities.short_description = "✗ Reject selected activities"
    
    def mark_as_manual(self, request, queryset):
        """Mark selected activities as manual entries."""
        updated = queryset.update(is_manual=True)
        self.message_user(request, f"{updated} activities marked as manual.")
    mark_as_manual.short_description = "📝 Mark as manual entries"
    
    def mark_as_catalog(self, request, queryset):
        """Mark selected activities as catalog entries."""
        updated = queryset.update(is_manual=False)
        self.message_user(request, f"{updated} activities marked as catalog items.")
    mark_as_catalog.short_description = "📚 Mark as catalog entries"
    
    def duplicate_activities(self, request, queryset):
        """Create duplicates of selected activities for modification."""
        count = 0
        for activity in queryset:
            # Create a duplicate
            activity.pk = None
            activity.title = f"{activity.title} (Copy)"
            activity.slug = None  # Will be auto-generated
            activity.status = 'pending'
            activity.approved_at = None
            activity.save()
            count += 1
        self.message_user(request, f"{count} activities duplicated successfully.")
    duplicate_activities.short_description = "📋 Duplicate selected activities"
    
    def get_queryset(self, request):
        """Optimize queryset with prefetch_related and annotations."""
        return super().get_queryset(request).prefetch_related(
            'recommended_professions'
        ).annotate(
            log_entries_count_annotation=Count('log_entries')
        )
