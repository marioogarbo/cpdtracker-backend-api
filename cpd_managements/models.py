from django.db import models
from django.utils import timezone
from django.conf import settings
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from config.utils import CustomShortUUIDField
from decimal import Decimal

User = settings.AUTH_USER_MODEL


class CredentialingProgram(models.Model):
    """
    Represents a credentialing program that professionals can enroll in to meet CPD requirements.
    """

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    ]

    METHODOLOGY = [
        ('hours_based', 'Hours Based'),
        ('points_based', 'Points Based'),
        ('hybrid', 'Hybrid (Hours and Points)'),
    ]

    id = CustomShortUUIDField(primary_key=True, prefix='program_', editable=False)
    name = models.CharField(
        max_length=255, unique=True,
        help_text="Name of the credentialing program. Do not abbreviate or use acronyms."
    )
    slug = models.SlugField(
        max_length=255, unique=True, blank=True, editable=False,
        help_text="URL-friendly version of the program name, auto-generated from the name field."
    )
    description = models.TextField(blank=True, null=True)
    provider = models.CharField(
        max_length=255,
        help_text="Name of the organization providing the credentialing program. Do not abbreviate or use acronyms."
    )
    renewal_period_months = models.PositiveIntegerField(
        default=12,
        help_text="Renewal interval, in months (e.g. 3 for quarterly, 6 for semi-annual, 10 for every 10 months)."
    )
    methodology = models.CharField(
        max_length=20, choices=METHODOLOGY, default='points_based',
        help_text="Methodology used for CPD requirements."
    )
    required_points = models.DecimalField(
        max_digits=6, decimal_places=1, default=Decimal('0.0'),
        help_text="Total points required for the credentialing program."
    )
    required_hours = models.DecimalField(
        max_digits=6, decimal_places=1, default=Decimal('0.0'),
        help_text="Total hours required for the credentialing program."
    )
    allow_carryover = models.BooleanField(
        default=False,
        help_text="Allow carryover of unused hours/points to the next cycle"
    )
    max_carryover_points = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True,
        help_text="Maximum carryover points allowed."
    )
    max_carryover_hours = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True,
        help_text="Maximum carryover hours allowed."
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='draft',
        help_text="Status of the credentialing program. Draft/Archived programs are not visible to users."
    )
    
    # Metadata and tracking
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_credentials')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        unique_together = ('name', 'provider')
        verbose_name = "Credentialing Program"
        verbose_name_plural = "Credentialing Programs"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def uses_points(self):
        """Check if this program uses points for tracking CPD requirements."""
        return self.methodology in ['points_based', 'hybrid']
    
    @property
    def uses_hours(self):
        """Check if this program uses hours for tracking CPD requirements."""
        return self.methodology in ['hours_based', 'hybrid']
    
    @property
    def requires_points(self):
        """Check if this program requires points and has a non-zero requirement."""
        return self.uses_points and self.required_points > 0
    
    @property
    def requires_hours(self):
        """Check if this program requires hours and has a non-zero requirement."""
        return self.uses_hours and self.required_hours > 0


class CredentialCriteria(models.Model):
    """
    Represents rules for CPD activity categories within a credentialing program.
    Each program can define its own custom categories with specific rules.
    """

    id = CustomShortUUIDField(primary_key=True, prefix='rule_', editable=False)
    program = models.ForeignKey(
        CredentialingProgram, on_delete=models.CASCADE, related_name='category_rules',
        help_text="The credentialing program this criteria belongs to."
    )
    category_code = models.CharField(
        max_length=50,
        default='other',
        help_text="Unique code/identifier for this category within the program (e.g., '1', '2', 'course', 'formal_ed')"
    )
    category_name = models.CharField(
        max_length=200,
        default='Other Activity',
        help_text="Display name for this category (e.g., 'Formal education and training', 'Short courses')"
    )
    category_description = models.TextField(
        blank=True, null=True,
        help_text="Detailed description of what activities fall under this category"
    )
    points_per_hour = models.DecimalField(
        max_digits=5, decimal_places=1, default=Decimal('0.00'),
        help_text="Points awarded per hour of activity in this category."
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which this category should be displayed"
    )

    class Meta:
        unique_together = [['program', 'category_code']]
        ordering = ['sort_order', 'category_code']
        verbose_name = "Program Category Rule"
        verbose_name_plural = "Program Category Rules"

    def __str__(self):
        return f"{self.program.name} - {self.category_name}"


class Enrollment(models.Model):
    """
    Represents a user's enrollment in a credentialing program.
    """

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
        ('deleted', 'Deleted'),
    ]

    id = CustomShortUUIDField(primary_key=True, prefix='enroll_', editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='program_enrollments',
        limit_choices_to={'role': 'professional'},
        help_text="The user enrolled in the credentialing program."
    )
    program = models.ForeignKey(
        CredentialingProgram, on_delete=models.CASCADE, related_name='enrollments',
        help_text="The credentialing program the user is enrolled in."
    )
    cycle_start_date = models.DateField(
        help_text="Start date of this enrollment cycle. Cannot be in the future."
    )
    cycle_end_date = models.DateField(
        help_text="End date of this enrollment cycle"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='active',
        help_text="Current status of the enrollment cycle"
    )
    enrollment_date = models.DateTimeField(
        default=timezone.now,
        help_text="Date when the user enrolled in the program cycle"
    )
    accumulated_hours = models.DecimalField(
        max_digits=6, decimal_places=1, default=0,
        help_text="Total approved hours accumulated in this cycle including carryover"
    )
    accumulated_points = models.DecimalField(
        max_digits=6, decimal_places=1, default=0,
        help_text="Total approved points accumulated in this cycle including carryover"
    )
    applied_carryover_hours = models.DecimalField(
        max_digits=5, decimal_places=1, default=0,
        help_text="Hours carried over from the previous cycle"
    )
    applied_carryover_points = models.DecimalField(
        max_digits=5, decimal_places=1, default=0,
        help_text="Points carried over from the previous cycle"
    )

    class Meta:
        unique_together = [['user', 'program', 'cycle_start_date']]
        ordering = ['-cycle_start_date', 'user']
        verbose_name = "User Program Enrollment"
        verbose_name_plural = "User Program Enrollments"
    
    def __str__(self):
        return f"{self.user.email} - {self.program.name} ({self.cycle_start_date} to {self.cycle_end_date})"
    
    @property
    def is_current_cycle_active(self):
        """Checks if the enrollment cycle is currently active based on dates."""
        if not self.cycle_start_date or not self.cycle_end_date:
            return False
        today = timezone.now().date()
        return self.cycle_start_date <= today <= self.cycle_end_date

    def update_accumulated_totals(self):
        """
        Recalculates and updates accumulated_hours and accumulated_points
        based on all log details for this enrollment cycle.
        """
        # Get all log details for this enrollment cycle
        all_details = self.log_details.all()
        
        # Aggregate current cycle hours and points
        current_cycle_hours = all_details.aggregate(total=models.Sum('total_hours'))['total'] or Decimal('0.0')
        current_cycle_points = all_details.aggregate(total=models.Sum('total_points'))['total'] or Decimal('0.0')
        
        # Ensure results are Decimal and correctly quantized
        self.accumulated_hours = (Decimal(current_cycle_hours) + Decimal(self.applied_carryover_hours)).quantize(Decimal('0.1'))
        self.accumulated_points = (Decimal(current_cycle_points) + Decimal(self.applied_carryover_points)).quantize(Decimal('0.1'))
        
        # Save the updated totals
        super(Enrollment, self).save(update_fields=['accumulated_hours', 'accumulated_points'])

    def clean(self):
        """Validate enrollment data"""
        super().clean()
        
        # Ensure cycle_end_date is not before cycle_start_date
        if self.cycle_end_date and self.cycle_start_date and self.cycle_end_date < self.cycle_start_date:
            raise ValidationError({'cycle_end_date': 'Enrollment cycle end date cannot be before start date.'})
        
        # Ensure cycle_start_date is not in the future
        if self.cycle_start_date and self.cycle_start_date > timezone.now().date():
            raise ValidationError({'cycle_start_date': 'Enrollment cycle start date cannot be in the future.'})
        
        # Ensure only one active enrollment per program per user
        if self.status == 'active':
            existing_active = Enrollment.objects.filter(
                user=self.user,
                program=self.program,
                status='active'
            ).exclude(pk=self.pk)  # Exclude current instance when updating
            
            if existing_active.exists():
                existing_enrollment = existing_active.first()
                raise ValidationError({
                    'program': f'You already have an active enrollment in {self.program.name} '
                              f'(cycle: {existing_enrollment.cycle_start_date} to {existing_enrollment.cycle_end_date}). '
                              f'Please complete or cancel your existing enrollment before creating a new one.'
                })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)