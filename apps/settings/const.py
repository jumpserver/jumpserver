from django.db.models import TextChoices


class ImportStatus(TextChoices):
    ok = 'ok', 'Ok'
    pending = 'pending', 'Pending'
    error = 'error', 'Error'
