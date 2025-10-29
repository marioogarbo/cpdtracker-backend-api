from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import CredentialingProgram

CACHE_KEY_PREFIX = 'available_programs'
PROGRAM_DETAIL_CACHE_KEY_PREFIX = 'program_detail'

@receiver(post_save, sender=CredentialingProgram)
def clear_available_programs_cache_on_save(sender, instance, **kwargs):
    # Clear the cache for the available programs list when a CredentialingProgram is saved
    cache.delete_pattern(f'*{CACHE_KEY_PREFIX}*')

@receiver(post_delete, sender=CredentialingProgram)
def clear_available_programs_cache_on_delete(sender, instance, **kwargs):
    # Clear the cache for the available programs list when a CredentialingProgram is deleted
    cache.delete_pattern(f'*{CACHE_KEY_PREFIX}*')

@receiver(post_save, sender=CredentialingProgram)
def clear_program_detail_cache_on_save(sender, instance, **kwargs):
    # Clear the cache for the program detail view when a CredentialingProgram is saved
    cache.delete_pattern(f'*{PROGRAM_DETAIL_CACHE_KEY_PREFIX}*')

@receiver(post_delete, sender=CredentialingProgram)
def clear_program_detail_cache_on_delete(sender, instance, **kwargs):
    # Clear the cache for the program detail view when a CredentialingProgram is deleted
    cache.delete_pattern(f'*{PROGRAM_DETAIL_CACHE_KEY_PREFIX}*') 