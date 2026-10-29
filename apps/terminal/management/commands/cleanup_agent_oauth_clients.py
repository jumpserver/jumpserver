from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from oauth2_provider.models import get_application_model
from redis.exceptions import RedisError

from authentication.backends.oauth2_provider.agent_registration import REGISTRATION_LOCK
from common.utils.lock import DistributedLock
from terminal.models import AgentApplication


class Command(BaseCommand):
    help = 'Remove a bounded batch of old dynamic Agent clients that have never been authorized or referenced.'

    def add_arguments(self, parser):
        parser.add_argument('--older-than-days', type=int, default=7)
        parser.add_argument('--limit', type=int, default=100)

    def handle(self, *args, **options):
        if not 1 <= options['older_than_days'] <= 3650 or not 1 <= options['limit'] <= 1000:
            raise CommandError('Use 1-3650 days and a limit of 1-1000 clients')
        cutoff = timezone.now() - timedelta(days=options['older_than_days'])
        Application = get_application_model()
        lock, acquired, removed = DistributedLock(REGISTRATION_LOCK, expire=60), False, 0
        try:
            acquired = lock.acquire(blocking=False)
            if not acquired:
                raise CommandError('Agent client registration is busy; retry later')
            candidates = list(Application.objects.filter(
                registration_source=Application.RegistrationSource.DCR, created__lt=cutoff,
                agent_registration__isnull=False, agent_registration__date_authorized__isnull=True,
            ).order_by('created', 'pk').values_list('pk', flat=True)[:options['limit']])
            for pk in candidates:
                with transaction.atomic():
                    # Authorization code issuance uses the same lock order.
                    application = Application.objects.select_for_update().filter(
                        pk=pk, registration_source=Application.RegistrationSource.DCR, created__lt=cutoff,
                    ).first()
                    if application is None:
                        continue
                    registration = AgentApplication.objects.select_for_update().filter(
                        application=application, date_authorized__isnull=True,
                    ).first()
                    if registration is None:
                        continue
                    # Include all organizations and future related authority
                    # records; never cascade-delete an existing grant or audit.
                    referenced = any(
                        relation.related_model._base_manager.filter(**{relation.field.name: application}).exists()
                        for relation in application._meta.related_objects
                        if relation.related_model is not AgentApplication
                    )
                    if referenced:
                        continue
                    if not lock.locked_by_me():
                        raise CommandError('Registration lock expired; retry cleanup')
                    try:
                        with transaction.atomic():
                            application.delete()
                    except ProtectedError:
                        continue
                    removed += 1
        except RedisError as exc:
            raise CommandError('Registration coordination is unavailable') from exc
        finally:
            if acquired:
                try:
                    lock.release()
                except RedisError:
                    pass
        self.stdout.write(f'Removed {removed} unused Agent OAuth client(s).')
