from django.apps import AppConfig

class CpdManagementsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cpd_managements'

    def ready(self):
        import cpd_managements.signals  # noqa
