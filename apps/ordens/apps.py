from django.apps import AppConfig


class OrdensConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ordens"
    verbose_name = "Ordens de Serviço"

    def ready(self):
        from . import signals  # noqa: F401
