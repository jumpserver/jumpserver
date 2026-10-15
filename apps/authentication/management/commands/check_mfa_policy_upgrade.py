"""Read-only audit before enforcing the system MFA allow-list on custom users."""
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.module_loading import import_string

from authentication.mfa.policy import get_allowed_mfa_types
from users.models import User


def assess_user(user, backends):
    old_policy = set(user.allowed_mfa_types or get_allowed_mfa_types())
    new_policy = get_allowed_mfa_types(user)
    before = {backend.name for backend in backends if backend.name in old_policy}
    after = before & new_policy
    removed = before - after
    if not removed:
        return None
    active_before = {
        backend.name for backend in backends
        if backend.name in before and backend(user).is_active()
    }
    active_after = active_before & after
    return {
        'user_id': str(user.pk),
        'username': user.username,
        'removed_methods': sorted(removed),
        'remaining_methods': sorted(after),
        'previous_active_methods': sorted(active_before),
        'remaining_active_methods': sorted(active_after),
        'requires_attention': bool(
            user.is_active and user.mfa_enabled and active_before and not active_after
        ),
    }


class Command(BaseCommand):
    help = 'Report MFA methods lost when custom user policies are limited by system policy. No data is changed.'

    def add_arguments(self, parser):
        parser.add_argument('--database', default='default')
        parser.add_argument(
            '--fail-on-risk', action='store_true',
            help='Exit with an error if an enabled MFA user loses all active methods.',
        )

    def handle(self, *args, **options):
        backends = [import_string(path) for path in settings.MFA_BACKENDS]
        backends = [backend for backend in backends if backend.global_enabled()]
        users = User.objects.using(options['database']).exclude(allowed_mfa_types=[])
        affected = risks = 0
        for user in users.iterator(chunk_size=500):
            result = assess_user(user, backends)
            if result is None:
                continue
            affected += 1
            risks += int(result['requires_attention'])
            self.stdout.write(json.dumps(result, ensure_ascii=False))
        self.stdout.write(json.dumps({
            'affected_users': affected,
            'users_requiring_attention': risks,
        }))
        if risks and options['fail_on_risk']:
            raise CommandError('Some users would lose all active MFA methods. Review the reported policies before rollout.')
