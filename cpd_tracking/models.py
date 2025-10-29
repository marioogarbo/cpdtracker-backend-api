from django.db import models
from django.utils import timezone
from django.conf import settings
from config.utils import CustomShortUUIDField
from cpd_activities.models import CPDActivity
from decimal import Decimal
from cpd_managements.models import CredentialingProgram, CredentialCriteria, Enrollment

User = settings.AUTH_USER_MODEL

class CPDLogEntry(models.Model):
    """
    A User Professional's log entry for a completed CPD activity.
    This can be either a from catalog activity or a manual entry.
    """

    ACTIVITY_TYPE_CHOICES = [
        ('course', 'Course'),
        ('workshop', 'Workshop'),
        ('seminar', 'Seminar'),
        ('webinar', 'Webinar'),
        ('conference', 'Conference'),
        ('certification', 'Certification'),
        ('self_study', 'Self Study'),
        ('mentoring', 'Mentoring'),
        ('research', 'Research'),
        ('other', 'Other'),
    ]

    id = CustomShortUUIDField(primary_key=True, prefix='logentry_', editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='cpd_log_entries',
        help_text="The professional user who logged this activity."
    )
    cpd_activity = models.ForeignKey(
        CPDActivity, on_delete=models.CASCADE, null=True, blank=True, related_name='log_entries',
        help_text="Link to a pre-defined catalog activity (null for manual entries)"
    )
    is_manual = models.BooleanField(
        default=True,
        help_text="Whether this is a manual entry (True) or catalog activity (False)"
    )
    activity_type = models.CharField(
        max_length=20, choices=ACTIVITY_TYPE_CHOICES, default='other',
        help_text="Type/category of the CPD activity"
    )
    
    # Fields for manual entries
    manual_title = models.CharField(
        max_length=200, blank=True, null=True,
        help_text="Title for manual entries (not used for catalog activities)"
    )
    manual_description = models.TextField(
        blank=True, null=True,
        help_text="Description for manual entries (not used for catalog activities)"
    )
    manual_provider = models.CharField(
        max_length=200, blank=True, null=True,
        help_text="Provider for manual entries (not used for catalog activities)"
    )
    
    hours_spent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.0'),
        help_text="Total hours spent on the CPD activity."
    )
    completed_at = models.DateField(help_text="Date the CPD activity was completed.")
    start_datetime = models.DateTimeField(
        null=True, blank=True, 
        help_text="Start date and time of the activity"
    )
    end_datetime = models.DateTimeField(
        null=True, blank=True, 
        help_text="End date and time of the activity"
    )
    notes = models.TextField(
        blank=True, null=True, 
        help_text="Additional notes or reflections by the user."
    )
    # Metadata & Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "CPD Log Entry"
        verbose_name_plural = "CPD Log Entries"
        ordering = ['-completed_at', '-created_at']
        unique_together = [['user', 'cpd_activity', 'completed_at']]
        indexes = [
            models.Index(fields=['completed_at']),
            models.Index(fields=['is_manual']),
            models.Index(fields=['activity_type']),
        ]
    
    @property
    def title(self):
        """Get the title for this log entry"""
        if self.cpd_activity:
            return self.cpd_activity.title
        elif self.manual_title:
            return self.manual_title
        else:
            # Fallback for entries without manual_title
            return f"Manual Entry - {self.get_activity_type_display()}"
    
    @property
    def category(self):
        """Get the category for this log entry - alias for activity_type for backward compatibility"""
        return self.activity_type
    
    def __str__(self):
        return f"{self.title} - {self.completed_at.strftime('%Y-%m-%d')}"

class Evidence(models.Model):
    """
    Evidence supporting a CPD log entry (certificates, documents, URLs, etc.)
    """

    id = CustomShortUUIDField(primary_key=True, prefix='evidence_', editable=False)
    log_entry = models.ForeignKey(CPDLogEntry, on_delete=models.CASCADE, related_name='evidences')
    type = models.CharField(
        max_length=50, 
        choices=[
            ('file', 'File Upload'),
            ('url', 'URL Link')
        ],
        default='file',
        help_text="Type of evidence provided for the CPD activity."
    )
    file = models.FileField(
        upload_to='cpd_evidence/', 
        blank=True, null=True, 
        help_text="Uploaded evidence file (e.g., certificate)."
    )
    url = models.URLField(
        max_length=500, 
        blank=True, null=True, 
        help_text="URL to online evidence (e.g., certificate link)."
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, help_text="When the evidence was uploaded.")

    class Meta:
        verbose_name = "CPD Evidence"
        verbose_name_plural = "CPD Evidence"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Evidence for {self.log_entry.title}"


class CPDLogDetails(models.Model):
    """
    Details of how a CPD log entry applies to specific program enrollments.
    This acts as the junction table linking log entries to specific programs with calculated points.
    """

    id = CustomShortUUIDField(primary_key=True, prefix='logdetail_', editable=False)
    log_entry = models.ForeignKey(
        CPDLogEntry, on_delete=models.CASCADE, related_name='log_details',
        help_text="The CPD log entry"
    )
    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name='log_details',
        help_text="The user's program enrollment cycle this activity applies to"
    )
    applied_criteria = models.ForeignKey(
        CredentialCriteria, on_delete=models.SET_NULL, null=True, blank=True, related_name='applied_log_details',
        help_text="The credential criteria used for points calculation"
    )
    program_category = models.ForeignKey(
        CredentialCriteria, on_delete=models.SET_NULL, null=True, blank=True, related_name='selected_log_details',
        help_text="The program-specific category selected for this activity (replaces program_category_code)"
    )
    program_category_code = models.CharField(
        max_length=50, blank=True, null=True,
        help_text="Legacy field - kept for backward compatibility, use program_category instead"
    )
    points_per_hour = models.DecimalField(
        max_digits=5, decimal_places=1, default=Decimal('0.0'),
        help_text="Points awarded per hour based on program criteria"
    )
    total_points = models.DecimalField(
        max_digits=6, decimal_places=1, default=Decimal('0.0'),
        help_text="Total points calculated for this program"
    )
    total_hours = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.0'),
        help_text="Hours counted towards this program (may be capped)"
    )
    validated_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When this entry was validated for the program"
    )
    
    # Metadata & Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "CPD Log Detail"
        verbose_name_plural = "CPD Log Details"
        ordering = ['-created_at']
        unique_together = [['log_entry', 'enrollment']]
        indexes = [
            models.Index(fields=['enrollment']),
            models.Index(fields=['log_entry']),
        ]

    def __str__(self):
        return f"{self.log_entry} -> {self.enrollment.program.name}"

    def calculate_points(self):
        """Calculate points based on program rules and selected category."""
        points = Decimal('0.0')
        hours = self.log_entry.hours_spent
        
        # Default points per hour
        self.points_per_hour = Decimal('1.0')
        
        # Primary: Use direct FK reference to CredentialCriteria
        if self.program_category:
            # Direct FK lookup - much more efficient and reliable
            self.applied_criteria = self.program_category
            self.points_per_hour = self.program_category.points_per_hour
        # Legacy: If program_category_code is provided (backward compatibility)
        elif self.program_category_code:
            try:
                criteria = CredentialCriteria.objects.get(
                    program=self.enrollment.program,
                    category_code=self.program_category_code
                )
                self.applied_criteria = criteria
                self.program_category = criteria  # Upgrade to FK reference
                self.points_per_hour = criteria.points_per_hour
            except CredentialCriteria.DoesNotExist:
                # Category not found, use default
                pass
        else:
            # Fallback: try to match by legacy activity_type (for backward compatibility)
            if self.log_entry.cpd_activity:
                try:
                    criteria = CredentialCriteria.objects.get(
                        program=self.enrollment.program,
                        category_code=self.log_entry.cpd_activity.activity_type
                    )
                    self.applied_criteria = criteria
                    self.program_category = criteria  # Set FK reference
                    self.points_per_hour = criteria.points_per_hour
                except CredentialCriteria.DoesNotExist:
                    # Use activity default points per hour if available
                    if self.log_entry.cpd_activity.default_points_per_hour:
                        self.points_per_hour = self.log_entry.cpd_activity.default_points_per_hour
                        
        # Calculate total points
        points = hours * self.points_per_hour
                
        self.total_points = points.quantize(Decimal('0.1'))
        self.total_hours = hours
        return self.total_points

    def save(self, *args, **kwargs):
        if not self.pk or 'total_points' not in kwargs.get('update_fields', []):
            self.calculate_points()
        
        super().save(*args, **kwargs)
        
        # Update enrollment totals
        self.enrollment.update_accumulated_totals()