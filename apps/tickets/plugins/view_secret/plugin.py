from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone

from ..base import TicketPlugin


class Plugin(TicketPlugin):
    type = 'view_secret'
    label = _('View account password')
    self_service = True
    creation_modes = ('manual', 'operation')
    execution_mode = 'automatic'
    request_serializer = 'tickets.plugins.view_secret.serializer.RequestSerializer'

    def build_context(self, ticket):
        from ..resources import account_context
        context = account_context(ticket)
        context.update(actions=['view_secret'], duration=ticket.request_data['duration'])
        return context

    def validate_submission(self, ticket, context):
        from tickets.workflow.errors import WorkflowConfigurationError
        if settings.SECURITY_DISABLE_VIEW_SECRET:
            raise WorkflowConfigurationError('Account password viewing is disabled.')

    def on_approved(self, instance, ticket):
        from datetime import timedelta
        from accounts.const import SecretType
        from accounts.models import Account
        from tickets.models import TicketSecretAccess
        from tickets.workflow.errors import WorkflowConfigurationError

        if settings.SECURITY_DISABLE_VIEW_SECRET:
            raise WorkflowConfigurationError('Account password viewing is disabled.')
        snapshots = [a for a in instance.context['accounts'] if a['secret_type'] == SecretType.PASSWORD]
        account_ids = [a['id'] for a in snapshots]
        assets = instance.context['assets']
        if len(assets) != 1 or not account_ids:
            raise WorkflowConfigurationError('The requested password accounts are no longer available.')
        accounts = Account.objects.filter(
            pk__in=account_ids, asset_id=assets[0]['id'], asset__org_id=instance.org_id,
            asset__is_active=True, secret_type=SecretType.PASSWORD, is_active=True,
        )
        if accounts.count() != len(account_ids):
            raise WorkflowConfigurationError('The requested password accounts are no longer available.')
        expires_at = timezone.now() + timedelta(seconds=instance.context['duration'])
        for account in accounts:
            TicketSecretAccess.objects.get_or_create(
                ticket=ticket, account_id=account.pk,
                defaults={'user_id': instance.applicant_id, 'org_id': instance.org_id,
                          'expires_at': expires_at},
            )
        return {'action': 'grant_secret_access', 'ticket': str(ticket.pk),
                'resources': [{'type': 'account', 'id': str(account.pk), 'name': account.name}
                              for account in accounts]}

    def get_available_actions(self, ticket, user):
        return self.get_secret_access(ticket, user)[0]

    def get_secret_access(self, ticket, user):
        """Return usable actions and an explanation without loading account secrets."""
        from accounts.const import SecretType
        from accounts.models import Account
        from orgs.utils import tmp_to_org
        from tickets.workflow.approvers import available_users

        if not user or not user.is_authenticated or user.pk != ticket.applicant_id:
            return [], {'state': 'not_applicant'}
        if settings.SECURITY_DISABLE_VIEW_SECRET:
            return [], {'state': 'disabled'}
        if ticket.state == 'pending':
            return [], {'state': 'pending'}
        if ticket.state != 'approved':
            return [], {'state': 'unapproved'}
        if not available_users(ticket.org_id).filter(pk=user.pk).exists():
            return [], {'state': 'unavailable'}
        now = timezone.now()
        with tmp_to_org(ticket.org_id):
            grants = list(ticket.secret_accesses.filter(
                user_id=user.pk, org_id=ticket.org_id, is_active=True,
            ))
            accounts = dict(Account.objects.filter(
                pk__in=[grant.account_id for grant in grants], asset__org_id=ticket.org_id,
                asset__is_active=True, secret_type=SecretType.PASSWORD, is_active=True,
            ).values_list('pk', 'name'))
        grants = [grant for grant in grants if grant.account_id in accounts]
        usable = [grant for grant in grants if grant.expires_at > now]
        if usable:
            actions = [{'type': 'view_secret', 'account_id': str(grant.account_id),
                        'name': accounts[grant.account_id], 'expires_at': grant.expires_at.isoformat()}
                       for grant in usable]
            return actions, {'state': 'available',
                             'expires_at': min(grant.expires_at for grant in usable).isoformat()}
        if grants:
            return [], {'state': 'expired',
                        'expires_at': max(grant.expires_at for grant in grants).isoformat()}
        return [], {'state': 'unavailable'}
