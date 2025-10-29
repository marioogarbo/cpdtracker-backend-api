from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count, Q
from django.utils.safestring import mark_safe
from .models import CPDLogEntry, CPDLogDetails, Evidence


class UserEnrollmentFilter(admin.SimpleListFilter):
    """Custom filter to show CPD entries by user enrollment status."""
    title = 'User Enrollment Status'
    parameter_name = 'user_enrollment'
    
    def lookups(self, request, model_admin):
        return (
            ('has_active', 'Has Active Enrollments'),
            ('no_active', 'No Active Enrollments'),
            ('expired', 'Has Expired Enrollments'),
        )
    
    def queryset(self, request, queryset):
        from cpd_managements.models import Enrollment
        
        if self.value() == 'has_active':
            # Get users with active enrollments
            active_users = Enrollment.objects.filter(status='active').values_list('user_id', flat=True)
            return queryset.filter(user_id__in=active_users)
            
        elif self.value() == 'no_active':
            # Get users without active enrollments
            active_users = Enrollment.objects.filter(status='active').values_list('user_id', flat=True)
            return queryset.exclude(user_id__in=active_users)
            
        elif self.value() == 'expired':
            # Get users with expired enrollments
            expired_users = Enrollment.objects.filter(status='expired').values_list('user_id', flat=True)
            return queryset.filter(user_id__in=expired_users)
        
        return queryset


class CPDLogDetailsInline(admin.TabularInline):
    """Inline admin for CPD Log Details."""
    model = CPDLogDetails
    extra = 0
    readonly_fields = ['id', 'points_per_hour', 'total_points', 'total_hours', 'validated_at']
    fields = [
        'enrollment', 'applied_criteria', 'points_per_hour', 
        'total_points', 'total_hours', 'validated_at'
    ]
    verbose_name = "Program Assignment"
    verbose_name_plural = "Program Assignments"


class EvidenceInline(admin.TabularInline):
    """Inline admin for Evidence."""
    model = Evidence
    extra = 0
    readonly_fields = ['id', 'uploaded_at']
    fields = ['type', 'file', 'url', 'uploaded_at']
    verbose_name = "Evidence File"
    verbose_name_plural = "Evidence Files"


@admin.register(CPDLogEntry)
class CPDLogEntryAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for CPD Log Entries with comprehensive management features.
    """
    list_display = [
        'get_title', 'user_info', 'activity_type', 'get_category', 'hours_spent',
        'completed_at', 'program_count', 'user_enrolled_programs', 'total_points_earned', 'evidence_count'
    ]
    list_filter = [
        'activity_type', 'completed_at',
        'created_at', 'cpd_activity__provider', 'cpd_activity__activity_type',
        'log_details__enrollment__program', 'user__profession', UserEnrollmentFilter
    ]
    search_fields = [
        'cpd_activity__title', 'cpd_activity__description', 'cpd_activity__provider', 'user__email', 
        'user__first_name', 'user__last_name', 'notes'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'total_points_earned', 'evidence_count',
        'program_count', 'user_enrolled_programs', 'get_title', 'get_category'
    ]
    date_hierarchy = 'completed_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'cpd_activity', 'activity_type')
        }),
        ('Activity Details', {
            'fields': ('get_title', 'get_category')
        }),
        ('Time & Completion', {
            'fields': ('hours_spent', 'completed_at', 'start_datetime', 'end_datetime')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Summary', {
            'fields': ('program_count', 'user_enrolled_programs', 'total_points_earned', 'evidence_count'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [CPDLogDetailsInline, EvidenceInline]
    actions = [
        'export_to_csv', 'duplicate_entries'
    ]
    
    def get_title(self, obj):
        """Display activity title."""
        return obj.title
    get_title.short_description = "Title"
    get_title.admin_order_field = 'cpd_activity__title'
    
    def get_category(self, obj):
        """Display activity category."""
        return obj.category
    get_category.short_description = "Category"
    get_category.admin_order_field = 'cpd_activity__activity_type'
    
    def user_info(self, obj):
        """Display user information with link."""
        return format_html(
            '<a href="{}" title="{}">{}</a>',
            reverse('admin:users_user_change', args=[obj.user.pk]),
            obj.user.email,
            obj.user.get_full_name() or obj.user.email
        )
    user_info.short_description = "User"
    
    def program_count(self, obj):
        """Display count of assigned programs with link."""
        count = obj.log_details.count()
        if count == 0:
            return format_html('<span style="color: red;">No programs</span>')
        return format_html(
            '<a href="{}?log_entry__id__exact={}" style="color: green;" title="View program assignments">'
            '{} program{}</a>',
            reverse('admin:cpd_tracking_cpdlogdetails_changelist'),
            obj.id,
            count,
            's' if count != 1 else ''
        )
    program_count.short_description = "Programs"
    
    def user_enrolled_programs(self, obj):
        """Display user's active enrolled programs with links."""
        from cpd_managements.models import Enrollment
        active_enrollments = Enrollment.objects.filter(
            user=obj.user, 
            status='active'
        ).select_related('program')
        
        if not active_enrollments:
            return format_html('<span style="color: gray;">No active enrollments</span>')
        
        enrollment_links = []
        for enrollment in active_enrollments[:3]:  # Show first 3
            link = format_html(
                '<a href="{}" title="View enrollment details">{}</a>',
                reverse('admin:cpd_managements_enrollment_change', args=[enrollment.pk]),
                enrollment.program.name[:20] + ('...' if len(enrollment.program.name) > 20 else '')
            )
            enrollment_links.append(link)
        
        if len(active_enrollments) > 3:
            enrollment_links.append(f'... +{len(active_enrollments) - 3} more')
        
        # Add link to view all user enrollments
        all_enrollments_link = format_html(
            '<div><small><a href="{}?user__id__exact={}" target="_blank">View all enrollments →</a></small></div>',
            reverse('admin:cpd_managements_enrollment_changelist'),
            obj.user.pk
        )
        
        return format_html(
            '<div style="font-size: 0.9em;">{}<br/>{}</div>',
            '<br/>'.join(enrollment_links),
            all_enrollments_link
        )
    user_enrolled_programs.short_description = "User Enrollments"
    
    def total_points_earned(self, obj):
        """Calculate total points across all programs."""
        total = obj.log_details.aggregate(
            total=Sum('total_points')
        )['total'] or 0
        # Format the number first, then pass to format_html
        formatted_total = "{:.1f}".format(float(total))
        return format_html('<strong style="color: green;">{}</strong>', formatted_total)
    total_points_earned.short_description = "Total Points"
    
    def evidence_count(self, obj):
        """Display evidence count with link."""
        count = obj.evidences.count()
        if count == 0:
            return format_html('<span style="color: gray;">No evidence</span>')
        return format_html(
            '<a href="{}?log_entry__id__exact={}" style="color: blue;" title="View evidence files">'
            '{} file{}</a>',
            reverse('admin:cpd_tracking_evidence_changelist'),
            obj.id,
            count,
            's' if count != 1 else ''
        )
    evidence_count.short_description = "Evidence"
    
    def export_to_csv(self, request, queryset):
        """Export selected entries to CSV."""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="cpd_log_entries.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Title', 'User', 'Activity Type', 'Category', 'Hours', 
            'Completed Date', 'Total Points', 'Programs'
        ])
        
        for entry in queryset:
            writer.writerow([
                entry.title,
                entry.user.email,
                entry.get_activity_type_display(),
                entry.category,
                entry.hours_spent,
                entry.completed_at,
                entry.log_details.aggregate(Sum('total_points'))['total_points__sum'] or 0,
                entry.log_details.count()
            ])
        
        return response
    export_to_csv.short_description = "📁 Export to CSV"
    
    def duplicate_entries(self, request, queryset):
        """Create duplicates of selected entries for reuse."""
        count = 0
        for entry in queryset:
            # Create a duplicate
            original_pk = entry.pk
            entry.pk = None
            entry.save()
            count += 1
        self.message_user(request, f"{count} log entries duplicated successfully.")
    duplicate_entries.short_description = "📋 Duplicate selected entries"
    
    def get_queryset(self, request):
        """Optimize queryset with proper joins and annotations."""
        return super().get_queryset(request).select_related(
            'user', 'cpd_activity'
        ).prefetch_related('log_details', 'evidences').annotate(
            program_count_annotation=Count('log_details'),
            evidence_count_annotation=Count('evidences')
        )


@admin.register(CPDLogDetails)
class CPDLogDetailsAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for CPD Log Details with program tracking.
    """
    list_display = [
        'log_entry_info', 'user_email', 'enrollment_info', 'program_name',
        'points_per_hour', 'total_points', 'total_hours', 'validated_at'
    ]
    list_filter = [
        'validated_at', 'created_at', 
        'enrollment__program', 'enrollment__status'
    ]
    search_fields = [
        'log_entry__title', 'log_entry__user__email',
        'enrollment__program__name', 'enrollment__program__provider'
    ]
    readonly_fields = [
        'id', 'points_per_hour', 'total_points', 'total_hours', 
        'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Assignment Information', {
            'fields': ('id', 'log_entry', 'enrollment', 'applied_criteria')
        }),
        ('Calculated Values', {
            'fields': ('points_per_hour', 'total_points', 'total_hours')
        }),
        ('Validation', {
            'fields': ('validated_at',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['recalculate_points']
    
    def log_entry_info(self, obj):
        """Display log entry information with link."""
        return format_html(
            '<a href="{}" title="{}">{}</a>',
            reverse('admin:cpd_tracking_cpdlogentry_change', args=[obj.log_entry.pk]),
            "View full log entry details",
            obj.log_entry.title
        )
    log_entry_info.short_description = "Log Entry"
    
    def user_email(self, obj):
        """Display user email with link."""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:users_user_change', args=[obj.log_entry.user.pk]),
            obj.log_entry.user.email
        )
    user_email.short_description = "User"
    
    def enrollment_info(self, obj):
        """Display enrollment information with cycle details."""
        enrollment = obj.enrollment
        cycle_info = "{} - {}".format(
            enrollment.cycle_start_date.strftime('%m/%d/%y'),
            enrollment.cycle_end_date.strftime('%m/%d/%y')
        )
        
        # Calculate progress
        if enrollment.program.methodology == 'hours_based':
            progress = (float(enrollment.accumulated_hours) / float(enrollment.program.required_hours) * 100) if enrollment.program.required_hours > 0 else 0
            progress_text = "{}/{} hrs ({}%)".format(
                enrollment.accumulated_hours, enrollment.program.required_hours, round(progress, 0)
            )
        elif enrollment.program.methodology == 'points_based':
            progress = (float(enrollment.accumulated_points) / float(enrollment.program.required_points) * 100) if enrollment.program.required_points > 0 else 0
            progress_text = "{}/{} pts ({}%)".format(
                enrollment.accumulated_points, enrollment.program.required_points, round(progress, 0)
            )
        else:  # hybrid
            hours_progress = (float(enrollment.accumulated_hours) / float(enrollment.program.required_hours) * 100) if enrollment.program.required_hours > 0 else 0
            points_progress = (float(enrollment.accumulated_points) / float(enrollment.program.required_points) * 100) if enrollment.program.required_points > 0 else 0
            progress_text = "H: {}% / P: {}%".format(round(hours_progress, 0), round(points_progress, 0))
        
        return format_html(
            '<div style="font-size: 0.9em;">'
            '<div><a href="{}" title="View enrollment">{}</a></div>'
            '<div style="color: gray;">{}</div>'
            '<div style="color: {};">{}</div>'
            '</div>',
            reverse('admin:cpd_managements_enrollment_change', args=[enrollment.pk]),
            cycle_info,
            enrollment.get_status_display(),
            'green' if progress >= 100 else 'orange' if progress >= 50 else 'red',
            progress_text
        )
    enrollment_info.short_description = "Enrollment"
    
    def program_name(self, obj):
        """Display program name with link."""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:cpd_managements_credentialingprogram_change', args=[obj.enrollment.program.pk]),
            obj.enrollment.program.name
        )
    program_name.short_description = "Program"
    
    def recalculate_points(self, request, queryset):
        """Recalculate points for selected details."""
        count = 0
        for detail in queryset:
            detail.calculate_points()
            detail.save()
            count += 1
        self.message_user(request, f"Points recalculated for {count} assignments.")
    recalculate_points.short_description = "🔄 Recalculate points"
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related(
            'log_entry__user', 'enrollment__program', 'applied_criteria'
        )


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for Evidence files with file management.
    """
    list_display = [
        'log_entry_info', 'user_email', 'type', 'file_info', 'uploaded_at'
    ]
    list_filter = ['type', 'uploaded_at']
    search_fields = [
        'log_entry__title', 'log_entry__user__email', 'url'
    ]
    readonly_fields = ['id', 'uploaded_at', 'file_size']
    
    fieldsets = (
        ('Evidence Information', {
            'fields': ('id', 'log_entry', 'type')
        }),
        ('File Upload', {
            'fields': ('file', 'file_size'),
            'classes': ('collapse',)
        }),
        ('URL Link', {
            'fields': ('url',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('uploaded_at',),
            'classes': ('collapse',)
        }),
    )
    
    def log_entry_info(self, obj):
        """Display log entry information with link."""
        title_display = obj.log_entry.title[:50] + ('...' if len(obj.log_entry.title) > 50 else '')
        return format_html(
            '<a href="{}" title="{}">{}</a>',
            reverse('admin:cpd_tracking_cpdlogentry_change', args=[obj.log_entry.pk]),
            "View log entry: {}".format(obj.log_entry.title),
            title_display
        )
    log_entry_info.short_description = "Log Entry"
    
    def user_email(self, obj):
        """Display user email with link."""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:users_user_change', args=[obj.log_entry.user.pk]),
            obj.log_entry.user.email
        )
    user_email.short_description = "User"
    
    def file_info(self, obj):
        """Display file information or URL."""
        if obj.type == 'file' and obj.file:
            return format_html(
                '<a href="{}" target="_blank" title="Download file">{}</a>',
                obj.file.url,
                obj.file.name.split('/')[-1]
            )
        elif obj.type == 'url' and obj.url:
            url_display = obj.url[:50] + ('...' if len(obj.url) > 50 else '')
            return format_html(
                '<a href="{}" target="_blank" title="Open URL">{}</a>',
                obj.url,
                url_display
            )
        return format_html('<span style="color: gray;">No file/URL</span>')
    file_info.short_description = "File/URL"
    
    def file_size(self, obj):
        """Display file size if available."""
        if obj.file:
            try:
                size = obj.file.size
                if size < 1024:
                    return f"{size} bytes"
                elif size < 1024 * 1024:
                    return f"{size / 1024:.1f} KB"
                else:
                    return f"{size / (1024 * 1024):.1f} MB"
            except:
                return "Unknown"
        return "N/A"
    file_size.short_description = "File Size"
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('log_entry__user')
