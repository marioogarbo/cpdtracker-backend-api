from django.db import models
from django.conf import settings
from django.utils.text import slugify
from config.utils import CustomShortUUIDField
from users.models import Profession
from decimal import Decimal

User = settings.AUTH_USER_MODEL

class CPDActivity(models.Model):
    """
    Represents a CPD activity that can be offered to professionals.
    Activities can be pre-approved catalog items or manually entered by users.
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

    APPROVAL_STATUS_CHOICES = [
        ('pending', 'Pending Approval'), 
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    id = CustomShortUUIDField(primary_key=True, prefix='activity_', editable=False)
    title = models.CharField(max_length=400)
    slug = models.SlugField(max_length=400, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    thumbnail = models.ImageField(
        upload_to='cpd_activities/thumbnails/', 
        blank=True, null=True, 
        help_text="Thumbnail image for the activity."
    )
    link = models.URLField(
        max_length=500, blank=True, null=True, 
        help_text="Link to the activity details or registration page."
    )
    provider = models.CharField(
        max_length=255, blank=True, 
        help_text="Provider of the activity, if applicable."
    )
    activity_type = models.CharField(
        max_length=20, choices=ACTIVITY_TYPE_CHOICES, default='other',
        help_text="Category of activity for program-specific rule application"
    )
    start_datetime = models.DateTimeField(
        null=True, blank=True, help_text="Start date and time of the activity, if applicable."
    )
    end_datetime = models.DateTimeField(
        null=True, blank=True, help_text="End date and time of the activity, if applicable."
    )
    default_points_per_hour = models.DecimalField(
        max_digits=5, decimal_places=1, default=Decimal('1.0'),
        help_text="Default points awarded per hour for this activity"
    )
    recommended_professions = models.ManyToManyField(
        Profession, blank=True, related_name='recommended_cpd_activities',
        help_text="Professions for which this activity is recommended."
    )
    status = models.CharField(
        max_length=20, choices=APPROVAL_STATUS_CHOICES, default='approved',
        help_text="Approval status of the CPD activity"
    )
    is_manual = models.BooleanField(
        default=False,
        help_text="Indicates if this activity is manually professional user."
    )
    approved_at = models.DateTimeField(
        null=True, blank=True, 
        help_text="Timestamp when the activity was approved."
    )

    # Metadata & Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_cpd_activities',)
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the activity was created.")
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the activity was last updated.")

    class Meta:
        verbose_name = "CPD Activity"
        verbose_name_plural = "CPD Activities"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['title'], name='idx_cpd_activity_title'),
            models.Index(fields=['provider']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)