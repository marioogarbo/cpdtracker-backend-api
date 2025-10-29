from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import CPDActivity

CACHE_KEY_PREFIX = 'enhanced_cpd_activities'
CPD_DETAIL_CACHE_KEY_PREFIX = 'cpd_activity_detail'

@receiver(post_save, sender=CPDActivity)
def clear_enhanced_cpd_activities_cache_on_save(sender, instance, **kwargs):
    # Clear the cache for the enhanced activities list when a CPDActivity is saved
    cache.delete_pattern(f'*{CACHE_KEY_PREFIX}*')

@receiver(post_delete, sender=CPDActivity)
def clear_enhanced_cpd_activities_cache_on_delete(sender, instance, **kwargs):
    # Clear the cache for the enhanced activities list when a CPDActivity is deleted
    cache.delete_pattern(f'*{CACHE_KEY_PREFIX}*')

@receiver(post_save, sender=CPDActivity)
def clear_cpd_activity_detail_cache_on_save(sender, instance, **kwargs):
    # Clear the cache for the activity detail view when a CPDActivity is saved
    cache.delete_pattern(f'*{CPD_DETAIL_CACHE_KEY_PREFIX}*')

@receiver(post_delete, sender=CPDActivity)
def clear_cpd_activity_detail_cache_on_delete(sender, instance, **kwargs):
    # Clear the cache for the activity detail view when a CPDActivity is deleted
    cache.delete_pattern(f'*{CPD_DETAIL_CACHE_KEY_PREFIX}*') 