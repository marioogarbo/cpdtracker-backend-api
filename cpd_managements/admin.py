from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from django.utils.safestring import mark_safe
from django.utils import timezone
from .models import CredentialingProgram, CredentialCriteria, Enrollment


class RequirementsMetFilter(admin.SimpleListFilter):
    """Custom filter to show enrollments by requirements completion status."""
    title = 'Requirements Status'
    parameter_name = 'requirements_met'
    
    def lookups(self, request, model_admin):
        return (
            ('met', 'Requirements Met'),
            ('not_met', 'Requirements Not Met'),
            ('close', 'Close to Requirements (>80%)'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'met':
            # Filter for enrollments where requirements are met
            met_enrollments = []
            for enrollment in queryset:
                if enrollment.program.methodology == 'hours_based':
                    if enrollment.accumulated_hours >= enrollment.program.required_hours:
                        met_enrollments.append(enrollment.id)
                elif enrollment.program.methodology == 'points_based':
                    if enrollment.accumulated_points >= enrollment.program.required_points:
                        met_enrollments.append(enrollment.id)
                else:  # hybrid
                    points_met = not enrollment.program.uses_points or enrollment.accumulated_points >= enrollment.program.required_points
                    hours_met = not enrollment.program.uses_hours or enrollment.accumulated_hours >= enrollment.program.required_hours
                    if points_met and hours_met:
                        met_enrollments.append(enrollment.id)
            return queryset.filter(id__in=met_enrollments)
            
        elif self.value() == 'not_met':
            # Filter for enrollments where requirements are not met
            not_met_enrollments = []
            for enrollment in queryset:
                if enrollment.program.methodology == 'hours_based':
                    if enrollment.accumulated_hours < enrollment.program.required_hours:
                        not_met_enrollments.append(enrollment.id)
                elif enrollment.program.methodology == 'points_based':
                    if enrollment.accumulated_points < enrollment.program.required_points:
                        not_met_enrollments.append(enrollment.id)
                else:  # hybrid
                    points_met = not enrollment.program.uses_points or enrollment.accumulated_points >= enrollment.program.required_points
                    hours_met = not enrollment.program.uses_hours or enrollment.accumulated_hours >= enrollment.program.required_hours
                    if not (points_met and hours_met):
                        not_met_enrollments.append(enrollment.id)
            return queryset.filter(id__in=not_met_enrollments)
            
        elif self.value() == 'close':
            # Filter for enrollments close to meeting requirements (>80%)
            close_enrollments = []
            for enrollment in queryset:
                if enrollment.program.methodology == 'hours_based':
                    if enrollment.program.required_hours > 0:
                        progress = float(enrollment.accumulated_hours) / float(enrollment.program.required_hours)
                        if 0.8 <= progress < 1.0:
                            close_enrollments.append(enrollment.id)
                elif enrollment.program.methodology == 'points_based':
                    if enrollment.program.required_points > 0:
                        progress = float(enrollment.accumulated_points) / float(enrollment.program.required_points)
                        if 0.8 <= progress < 1.0:
                            close_enrollments.append(enrollment.id)
                else:  # hybrid
                    hours_progress = 0
                    points_progress = 0
                    if enrollment.program.required_hours > 0:
                        hours_progress = float(enrollment.accumulated_hours) / float(enrollment.program.required_hours)
                    if enrollment.program.required_points > 0:
                        points_progress = float(enrollment.accumulated_points) / float(enrollment.program.required_points)
                    
                    avg_progress = (hours_progress + points_progress) / 2
                    if 0.8 <= avg_progress < 1.0:
                        close_enrollments.append(enrollment.id)
            return queryset.filter(id__in=close_enrollments)
        
        return queryset


class CPDLogDetailsInline(admin.TabularInline):
    """Inline admin for viewing CPD Log Details within Enrollment."""
    from cpd_tracking.models import CPDLogDetails
    model = CPDLogDetails
    extra = 0
    readonly_fields = [
        'log_entry_info', 'applied_criteria', 'points_per_hour', 
        'total_points', 'total_hours', 'validated_at'
    ]
    fields = [
        'log_entry_info', 'applied_criteria', 'points_per_hour', 
        'total_points', 'total_hours', 'validated_at'
    ]
    verbose_name = "CPD Activity Detail"
    verbose_name_plural = "CPD Activity Details"
    can_delete = False
    
    def log_entry_info(self, obj):
        """Display log entry information."""
        if obj.log_entry:
            return format_html(
                '<div><strong>{}</strong><br/><small>{} • {} hrs</small></div>',
                obj.log_entry.title,
                obj.log_entry.completed_at.strftime('%Y-%m-%d'),
                obj.log_entry.hours_spent
            )
        return '-'
    log_entry_info.short_description = "CPD Activity"
    
    def has_add_permission(self, request, obj):
        return False


class CredentialCriteriaInline(admin.TabularInline):
    """Inline admin for managing category rules within a program."""
    model = CredentialCriteria
    extra = 1
    fields = ['category_code', 'category_name', 'category_description', 'points_per_hour', 'sort_order']
    verbose_name = "Category Rule"
    verbose_name_plural = "Category Rules"


@admin.register(CredentialingProgram)
class CredentialingProgramAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for Credentialing Programs with comprehensive management features.
    """
    list_display = [
        'name', 'provider', 'methodology', 'renewal_period_months', 'status', 
        'required_points_display', 'required_hours_display', 'enrollment_count', 'created_at'
    ]
    list_filter = [
        'status', 'methodology', 'allow_carryover', 'created_at',
        'renewal_period_months'
    ]
    search_fields = ['name', 'provider', 'description']
    readonly_fields = ['id', 'slug', 'created_at', 'updated_at', 'enrollment_count']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'slug', 'description', 'provider', 'status')
        }),
        ('CPD Requirements', {
            'fields': ('methodology', 'required_points', 'required_hours', 'renewal_period_months')
        }),
        ('Carryover Settings', {
            'fields': ('allow_carryover', 'max_carryover_points', 'max_carryover_hours'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at', 'enrollment_count'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [CredentialCriteriaInline]
    actions = ['activate_programs', 'archive_programs', 'draft_programs']
    
    def required_points_display(self, obj):
        """Display required points only if the program uses points."""
        if obj.uses_points:
            return f"{obj.required_points} pts" if obj.required_points > 0 else "0 pts"
        return format_html('<span style="color: gray;">N/A</span>')
    required_points_display.short_description = "Required Points"
    required_points_display.admin_order_field = 'required_points'
    
    def required_hours_display(self, obj):
        """Display required hours only if the program uses hours."""
        if obj.uses_hours:
            return f"{obj.required_hours} hrs" if obj.required_hours > 0 else "0 hrs"
        return format_html('<span style="color: gray;">N/A</span>')
    required_hours_display.short_description = "Required Hours"
    required_hours_display.admin_order_field = 'required_hours'
    
    def enrollment_count(self, obj):
        """Display count of active enrollments."""
        count = obj.enrollments.filter(status='active').count()
        if count == 0:
            return format_html('<span style="color: gray;">No enrollments</span>')
        return format_html(
            '<a href="{}?program__id__exact={}" style="color: green;">{} active enrollments</a>',
            reverse('admin:cpd_managements_enrollment_changelist'),
            obj.id,
            count
        )
    enrollment_count.short_description = "Active Enrollments"
    
    def activate_programs(self, request, queryset):
        """Bulk activate selected programs."""
        updated = queryset.update(status='active')
        self.message_user(request, f"{updated} programs activated successfully.")
    activate_programs.short_description = "Activate selected programs"
    
    def archive_programs(self, request, queryset):
        """Bulk archive selected programs."""
        updated = queryset.update(status='archived')
        self.message_user(request, f"{updated} programs archived.")
    archive_programs.short_description = "Archive selected programs"
    
    def draft_programs(self, request, queryset):
        """Mark selected programs as draft."""
        updated = queryset.update(status='draft')
        self.message_user(request, f"{updated} programs marked as draft.")
    draft_programs.short_description = "Mark as draft"
    
    def get_queryset(self, request):
        """Optimize queryset with annotation."""
        return super().get_queryset(request).annotate(
            active_enrollment_count=Count('enrollments', filter=Q(enrollments__status='active'))
        )


@admin.register(CredentialCriteria)
class CredentialCriteriaAdmin(admin.ModelAdmin):
    """
    Admin interface for managing CPD category rules within programs.
    """
    list_display = [
        'program', 'category_code', 'category_name', 'points_per_hour', 'sort_order', 'created_info'
    ]
    list_filter = ['program__methodology', 'program__status', 'program']
    search_fields = ['program__name', 'program__provider', 'category_code', 'category_name']
    readonly_fields = ['id']
    ordering = ['program', 'sort_order', 'category_code']
    
    fieldsets = (
        ('Rule Information', {
            'fields': ('id', 'program', 'category_code', 'category_name', 'category_description', 'points_per_hour', 'sort_order')
        }),
    )
    
    def created_info(self, obj):
        """Display when this rule was created."""
        return format_html(
            '<span style="color: gray; font-size: 0.9em;">Program created: {}</span>',
            obj.program.created_at.strftime('%Y-%m-%d')
        )
    created_info.short_description = "Info"
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('program')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for User Program Enrollments with comprehensive management features.
    """
    list_display = [
        'user_info', 'program', 'status', 'cycle_period', 'progress_display', 
        'requirements_status', 'carryover_info', 'enrollment_date', 'cycle_status'
    ]
    list_filter = [
        'status', 'program__methodology', 'program__status', 'program__provider',
        'cycle_start_date', 'enrollment_date', 'user__profession', RequirementsMetFilter
    ]
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name', 
        'program__name', 'program__provider', 'user__license_number'
    ]
    readonly_fields = [
        'id', 'enrollment_date', 'accumulated_hours', 'accumulated_points',
        'progress_display', 'requirements_status', 'cycle_status', 'log_entries_count'
    ]
    date_hierarchy = 'cycle_start_date'
    
    fieldsets = (
        ('Enrollment Information', {
            'fields': ('id', 'user', 'program', 'status', 'enrollment_date')
        }),
        ('Cycle Dates', {
            'fields': ('cycle_start_date', 'cycle_end_date', 'cycle_status')
        }),
        ('Progress Tracking', {
            'fields': ('accumulated_hours', 'accumulated_points', 'progress_display', 'requirements_status'),
            'classes': ('collapse',)
        }),
        ('Carryover Information', {
            'fields': ('applied_carryover_hours', 'applied_carryover_points'),
            'classes': ('collapse',)
        }),
        ('Activity Summary', {
            'fields': ('log_entries_count',),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [CPDLogDetailsInline]
    actions = ['activate_enrollments', 'complete_enrollments', 'cancel_enrollments', 'recalculate_totals', 'export_as_csv']
    
    def user_info(self, obj):
        """Display user information with profession and license."""
        profession = obj.user.profession.name if obj.user.profession else 'Not specified'
        license_info = f" (Lic: {obj.user.license_number})" if obj.user.license_number else ""
        
        return format_html(
            '<div><strong>{}</strong><br/><small style="color: gray;">{} • {}{}</small></div>',
            obj.user.get_full_name(),
            obj.user.email,
            profession,
            license_info
        )
    user_info.short_description = "User"
    user_info.admin_order_field = 'user__first_name'
    
    def cycle_period(self, obj):
        """Display the enrollment cycle period."""
        return format_html(
            '<span title="{} to {}">{} → {}</span>',
            obj.cycle_start_date,
            obj.cycle_end_date,
            obj.cycle_start_date.strftime('%m/%d/%y'),
            obj.cycle_end_date.strftime('%m/%d/%y')
        )
    cycle_period.short_description = "Cycle Period"
    cycle_period.admin_order_field = 'cycle_start_date'
    
    def progress_display(self, obj):
        """Display progress towards requirements with visual indicators."""
        if obj.program.methodology == 'hours_based':
            current = float(obj.accumulated_hours)
            required = float(obj.program.required_hours)
            unit = "hrs"
        elif obj.program.methodology == 'points_based':
            current = float(obj.accumulated_points)
            required = float(obj.program.required_points)
            unit = "pts"
        else:  # hybrid
            hours_current = float(obj.accumulated_hours)
            hours_required = float(obj.program.required_hours)
            points_current = float(obj.accumulated_points)
            points_required = float(obj.program.required_points)
            
            hours_percent = (hours_current / hours_required * 100) if hours_required > 0 else 0
            points_percent = (points_current / points_required * 100) if points_required > 0 else 0
            
            # Format strings first, then use in format_html
            hours_text = "Hours: {}/{} ({}%)".format(
                round(hours_current, 1), round(hours_required, 1), round(hours_percent, 0)
            )
            points_text = "Points: {}/{} ({}%)".format(
                round(points_current, 1), round(points_required, 1), round(points_percent, 0)
            )
            
            return format_html(
                '<div style="font-size: 0.9em;">'
                '<div>{}</div>'
                '<div>{}</div>'
                '</div>',
                hours_text, points_text
            )
        
        if required > 0:
            percentage = (current / required) * 100
            color = 'green' if percentage >= 100 else 'orange' if percentage >= 50 else 'red'
            
            # Format the progress text first
            progress_text = "{}/{} {} ({}%)".format(
                round(current, 1), round(required, 1), unit, round(percentage, 0)
            )
            
            return format_html(
                '<div style="color: {};">{}</div>',
                color, progress_text
            )
        else:
            return format_html('<span style="color: gray;">No requirements set</span>')
    progress_display.short_description = "Progress"
    
    def requirements_status(self, obj):
        """Display whether requirements are met."""
        if obj.program.methodology == 'hours_based':
            met = obj.accumulated_hours >= obj.program.required_hours
        elif obj.program.methodology == 'points_based':
            met = obj.accumulated_points >= obj.program.required_points
        else:  # hybrid
            hours_met = obj.accumulated_hours >= obj.program.required_hours
            points_met = obj.accumulated_points >= obj.program.required_points
            met = hours_met and points_met
        
        if met:
            return format_html('<span style="color: green; font-weight: bold;">✓ Requirements Met</span>')
        else:
            return format_html('<span style="color: red;">✗ Requirements Not Met</span>')
    requirements_status.short_description = "Status"
    
    def carryover_info(self, obj):
        """Display carryover information if applicable."""
        if obj.applied_carryover_hours > 0 or obj.applied_carryover_points > 0:
            info_parts = []
            if obj.applied_carryover_hours > 0:
                info_parts.append(f"{obj.applied_carryover_hours} hrs")
            if obj.applied_carryover_points > 0:
                info_parts.append(f"{obj.applied_carryover_points} pts")
            
            return format_html(
                '<span style="color: blue; font-size: 0.9em;" title="Carried over from previous cycle">↗ {}</span>',
                " + ".join(info_parts)
            )
        return format_html('<span style="color: gray;">-</span>')
    carryover_info.short_description = "Carryover"
    
    def cycle_status(self, obj):
        """Display whether the cycle is currently active based on dates."""
        if obj.is_current_cycle_active:
            return format_html('<span style="color: green;">🟢 Active Cycle</span>')
        elif obj.cycle_end_date < timezone.now().date():
            return format_html('<span style="color: orange;">🟡 Past Cycle</span>')
        else:
            return format_html('<span style="color: blue;">🔵 Future Cycle</span>')
    cycle_status.short_description = "Cycle Status"
    
    def log_entries_count(self, obj):
        """Display count of CPD log entries for this enrollment with navigation links."""
        count = obj.log_details.count()
        if count == 0:
            return format_html('<span style="color: gray;">No activities logged</span>')
        
        approved_count = obj.log_details.filter(status='approved').count()
        pending_count = obj.log_details.filter(status='pending').count()
        
        # Create link to view log details for this enrollment
        changelist_url = reverse('admin:cpd_tracking_cpdlogdetails_changelist')
        filter_url = f"{changelist_url}?enrollment__id__exact={obj.id}"
        
        return format_html(
            '<div style="font-size: 0.9em;">'
            '<div><a href="{}" target="_blank">Total: {} activities →</a></div>'
            '<div style="color: green;">Approved: {}</div>'
            '<div style="color: orange;">Pending: {}</div>'
            '</div>',
            filter_url, count, approved_count, pending_count
        )
    log_entries_count.short_description = "Activities"
    
    def activate_enrollments(self, request, queryset):
        """Bulk activate selected enrollments."""
        updated = queryset.update(status='active')
        self.message_user(request, f"{updated} enrollments activated successfully.")
    activate_enrollments.short_description = "Activate selected enrollments"
    
    def complete_enrollments(self, request, queryset):
        """Mark selected enrollments as completed."""
        updated = queryset.update(status='completed')
        self.message_user(request, f"{updated} enrollments marked as completed.")
    complete_enrollments.short_description = "Mark as completed"
    
    def cancel_enrollments(self, request, queryset):
        """Cancel selected enrollments."""
        updated = queryset.update(status='cancelled')
        self.message_user(request, f"{updated} enrollments cancelled.")
    cancel_enrollments.short_description = "Cancel selected enrollments"
    
    def recalculate_totals(self, request, queryset):
        """Recalculate accumulated totals for selected enrollments."""
        updated_count = 0
        for enrollment in queryset:
            enrollment.update_accumulated_totals()
            updated_count += 1
        self.message_user(request, f"Recalculated totals for {updated_count} enrollments.")
    recalculate_totals.short_description = "Recalculate accumulated totals"
    
    def export_as_csv(self, request, queryset):
        """Export selected enrollments as CSV."""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="enrollments_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'User Email', 'User Name', 'Profession', 'License Number',
            'Program Name', 'Program Provider', 'Methodology',
            'Status', 'Cycle Start', 'Cycle End', 'Enrollment Date',
            'Required Hours', 'Accumulated Hours', 'Hours Progress %',
            'Required Points', 'Accumulated Points', 'Points Progress %',
            'Carryover Hours', 'Carryover Points', 'Requirements Met'
        ])
        
        for enrollment in queryset:
            # Calculate progress percentages
            hours_progress = 0
            points_progress = 0
            if enrollment.program.required_hours > 0:
                hours_progress = (float(enrollment.accumulated_hours) / float(enrollment.program.required_hours)) * 100
            if enrollment.program.required_points > 0:
                points_progress = (float(enrollment.accumulated_points) / float(enrollment.program.required_points)) * 100
            
            # Determine if requirements are met
            if enrollment.program.methodology == 'hours_based':
                requirements_met = enrollment.accumulated_hours >= enrollment.program.required_hours
            elif enrollment.program.methodology == 'points_based':
                requirements_met = enrollment.accumulated_points >= enrollment.program.required_points
            else:  # hybrid
                requirements_met = (enrollment.accumulated_hours >= enrollment.program.required_hours and 
                                  enrollment.accumulated_points >= enrollment.program.required_points)
            
            writer.writerow([
                enrollment.user.email,
                enrollment.user.get_full_name(),
                enrollment.user.profession.name if enrollment.user.profession else '',
                enrollment.user.license_number or '',
                enrollment.program.name,
                enrollment.program.provider,
                enrollment.program.get_methodology_display(),
                enrollment.get_status_display(),
                enrollment.cycle_start_date,
                enrollment.cycle_end_date,
                enrollment.enrollment_date.date(),
                enrollment.program.required_hours,
                enrollment.accumulated_hours,
                "{:.1f}%".format(hours_progress),
                enrollment.program.required_points,
                enrollment.accumulated_points,
                "{:.1f}%".format(points_progress),
                enrollment.applied_carryover_hours,
                enrollment.applied_carryover_points,
                'Yes' if requirements_met else 'No'
            ])
        
        return response
    export_as_csv.short_description = "Export selected enrollments as CSV"

    
    def get_queryset(self, request):
        """Optimize queryset with related data."""
        return super().get_queryset(request).select_related(
            'user', 'user__profession', 'program'
        ).prefetch_related('log_details')