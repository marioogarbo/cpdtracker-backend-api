from django.apps import AppConfig


class CpdActivitiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cpd_activities'

    def ready(self):
        import cpd_activities.signals  # noqa
