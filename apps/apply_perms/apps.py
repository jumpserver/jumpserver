from django.apps import AppConfig


class ApplyPermsConfig(AppConfig):
    name = 'apply_perms'

    def ready(self):
        import apply_perms.signals