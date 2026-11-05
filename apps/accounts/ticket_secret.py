"""Reveal an account password under a ticket grant; never persist the plaintext."""
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response

from accounts.const import SecretType
from accounts.models import Account
from audits.const import ActionChoices
from audits.handler import create_or_update_operate_log
from orgs.utils import current_org, tmp_to_org
from tickets.models import TicketSecretAccess, WorkflowEvent
from tickets.workflow.approvers import available_users, user_snapshot


@transaction.atomic
def reveal_ticket_secret(request, account_id, ticket_id):
    if settings.SECURITY_DISABLE_VIEW_SECRET:
        raise PermissionDenied(_('Account password viewing is disabled.'))
    grant = TicketSecretAccess.objects.select_for_update().select_related('ticket').filter(
        ticket_id=ticket_id, account_id=account_id,
        user_id=request.user.pk, is_active=True, expires_at__gt=timezone.now(),
    ).first()
    if (not grant or grant.ticket.type != 'view_secret' or grant.ticket.state != 'approved' or
            grant.ticket.applicant_id != request.user.pk or grant.ticket.org_id != grant.org_id):
        raise PermissionDenied(_('No active approval for this account.'))
    if not current_org.is_root() and str(current_org.id) != str(grant.org_id):
        raise PermissionDenied(_('No active approval for this account.'))
    if not available_users(grant.org_id).filter(pk=request.user.pk).exists():
        raise PermissionDenied(_('The approved user is no longer in this organization.'))

    with tmp_to_org(grant.org_id):
        account = Account.objects.select_related('asset').filter(
            pk=account_id, asset__org_id=grant.org_id, asset__is_active=True,
            secret_type=SecretType.PASSWORD, is_active=True,
        ).first()
        if not account:
            raise NotFound(_('The approved account is no longer available.'))
        secret = account.secret
        if not secret:
            raise NotFound(_('The approved account has no password.'))
        WorkflowEvent.objects.create(
            instance=grant.ticket.workflow_instance, type='secret.viewed', actor=request.user,
            actor_snapshot=user_snapshot(request.user),
            data={'account_id': str(account.pk), 'account_name': account.name},
        )
        create_or_update_operate_log(
            ActionChoices.view, account._meta.verbose_name, resource=account,
            force=True, after={'Ticket': str(grant.ticket_id)},
            user=request.user, org_id=grant.org_id,
        )
    response = Response({'id': str(account.pk), 'name': account.name,
                         'username': account.username, 'secret': secret})
    response['Cache-Control'] = 'no-store'
    response['Pragma'] = 'no-cache'
    return response
