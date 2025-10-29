from django.apps import AppConfig


class CpdTrackingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cpd_tracking'
    
    def ready(self):
        import cpd_tracking.signals
