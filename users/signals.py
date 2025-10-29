from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import User

CACHE_KEY_PREFIX = 'user_profile'

@receiver(post_save, sender=User)
def clear_user_profile_cache_on_save(sender, instance, **kwargs):
    # Clear the cache for the user profile view when a User is saved
    # Use clear() to clear all cache since delete_pattern is not available in LocMemCache
    cache.clear()

@receiver(post_delete, sender=User)
def clear_user_profile_cache_on_delete(sender, instance, **kwargs):
    # Clear the cache for the user profile view when a User is deleted
    # Use clear() to clear all cache since delete_pattern is not available in LocMemCache
    cache.clear() 