from django.apps import AppConfig


class TournamentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tournaments"
    label = "tournaments"
    verbose_name = "Torneos"

    def ready(self):
        from .signals import register_signals
        register_signals()
