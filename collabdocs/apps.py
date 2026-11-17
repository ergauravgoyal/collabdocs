from django.apps import AppConfig


class CollabDocsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "collabdocs"

    def ready(self):
        from . import signals  # noqa: F401
