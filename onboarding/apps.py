from django.apps import AppConfig


class OnboardingConfig(AppConfig):
    """Configuration for the onboarding app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'onboarding'
    verbose_name = 'Onboarding & Supporter Management'

    def ready(self):
        """Import signal handlers when the app is ready."""
        # Import signals if we add any later
        pass
