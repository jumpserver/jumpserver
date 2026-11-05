"""Account-scoped password reveal backed by a completed ticket."""
from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.const import SecretType
from accounts.models import Account
from authentication.const import ConfirmType
from authentication.permissions import UserConfirmation
from orgs.utils import tmp_to_org, tmp_to_root_org
from tickets.workflow.approvers import available_users


class TicketSecretRequestSerializer(serializers.Serializer):
    ticket_id = serializers.UUIDField()


class AccountTicketSecretAPI(APIView):
    permission_classes = [IsAuthenticated, UserConfirmation.require(ConfirmType.MFA)]

    def post(self, request, pk):
        from accounts.ticket_secret import reveal_ticket_secret
        serializer = TicketSecretRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return reveal_ticket_secret(request, pk, serializer.validated_data['ticket_id'])


class TicketSecretOpenSerializer(serializers.Serializer):
    workflow_id = serializers.UUIDField()
    duration = serializers.IntegerField(min_value=60, max_value=86400, default=600)
    comment = serializers.CharField(max_length=4096, required=False, allow_blank=True, default='')


class AccountTicketSecretRequestAPI(APIView):
    """Start the same view_secret plugin from an account operation."""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def get_account(pk):
        if settings.SECURITY_DISABLE_VIEW_SECRET:
            raise PermissionDenied(_('Account password viewing is disabled.'))
        with tmp_to_root_org():
            account = Account.objects.select_related('asset').filter(
                pk=pk, is_active=True, secret_type=SecretType.PASSWORD,
                asset__is_active=True,
            ).first()
        if not account:
            raise NotFound(_('The requested password account is no longer available.'))
        return account

    @staticmethod
    def check_requester(request, org_id):
        with tmp_to_org(org_id):
            if not available_users(org_id).filter(pk=request.user.pk).exists() or not request.user.has_perm('tickets.view_ticket'):
                raise PermissionDenied()

    def get(self, request, pk):
        from orgs.models import Organization
        from tickets.models import Workflow

        account = self.get_account(pk)
        org_id = account.asset.org_id
        self.check_requester(request, org_id)
        with tmp_to_root_org():
            workflows = Workflow.objects.filter(
                org_id__in=[org_id, Organization.ROOT_ID], type='view_secret',
                is_system=False, enabled=True, active_version__published_at__isnull=False,
            ).order_by('name')
            return Response({'org_id': org_id, 'workflows': [
                {'id': str(flow.pk), 'name': flow.name} for flow in workflows
            ]})

    @transaction.atomic
    def post(self, request, pk):
        from tickets.const import TicketOrigin
        from tickets.serializers.plugin import PluginTicketApplySerializer
        from tickets.workflow.business import submit_ticket

        serializer = TicketSecretOpenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = self.get_account(pk)
        org_id = account.asset.org_id
        self.check_requester(request, org_id)
        with tmp_to_org(org_id):
            payload = {
                'type': 'view_secret', 'title': str(_('View password for %(account)s')) % {'account': account.name},
                'org_id': org_id, 'workflow_id': str(serializer.validated_data['workflow_id']),
                'comment': serializer.validated_data['comment'],
                'request_data': {'asset': str(account.asset_id), 'accounts': [account.username],
                                 'duration': serializer.validated_data['duration']},
            }
            ticket_serializer = PluginTicketApplySerializer(data=payload, context={'request': request})
            ticket_serializer.is_valid(raise_exception=True)
            ticket = ticket_serializer.save()
            ticket.origin = TicketOrigin.system
            ticket.save(update_fields=['origin'])
            submit_ticket(ticket)
        return Response({'id': str(ticket.pk), 'type': ticket.type, 'origin': ticket.origin}, status=201)
