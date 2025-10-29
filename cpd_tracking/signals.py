from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from .models import CPDLogEntry, CPDLogDetails


@receiver(post_save, sender=CPDLogEntry)
def handle_log_entry_changes(sender, instance, created, **kwargs):
    """
    Handle CPD log entry changes - update enrollment totals when log entry is modified.
    """
    if not created:
        # For updates, update enrollment totals
        update_enrollment_totals(instance)


@receiver(pre_delete, sender=CPDLogEntry)
def handle_log_entry_deletion(sender, instance, **kwargs):
    """
    Handle CPD log entry deletion - update enrollment totals when log entry is deleted.
    This needs to be pre_delete to access log_details before they're CASCADE deleted.
    """
    # Store the enrollments that need to be updated
    enrollments_to_update = set()
    for detail in instance.log_details.all():
        enrollments_to_update.add(detail.enrollment)
    
    # Store the enrollments in the instance for post_delete processing
    instance._enrollments_to_update = enrollments_to_update


@receiver(post_delete, sender=CPDLogEntry)
def update_enrollments_after_deletion(sender, instance, **kwargs):
    """
    Update enrollment totals after CPD log entry has been deleted.
    """
    # Update enrollments that were stored in pre_delete
    if hasattr(instance, '_enrollments_to_update'):
        for enrollment in instance._enrollments_to_update:
            enrollment.update_accumulated_totals()


@receiver(post_delete, sender=CPDLogDetails)
def handle_log_detail_deletion(sender, instance, **kwargs):
    """
    Handle CPD log detail deletion - update enrollment totals when log detail is deleted.
    """
    # Update the enrollment totals when a log detail is deleted
    instance.enrollment.update_accumulated_totals()


def update_enrollment_totals(log_entry):
    """
    Update enrollment totals when CPD log entry changes.
    """
    # Get all unique enrollments and update their totals
    enrollments = set()
    for detail in log_entry.log_details.all():
        enrollments.add(detail.enrollment)
    
    for enrollment in enrollments:
        enrollment.update_accumulated_totals()
