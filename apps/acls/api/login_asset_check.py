from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, RetrieveDestroyAPIView

from common.permissions import IsAppUser
from common.utils import reverse, lazyproperty
from tickets.models import Ticket
from orgs.utils import tmp_to_root_org, tmp_to_org
from ..models import LoginAssetACL
from .. import serializers


__all__ = ['LoginAssetCheckAPI', 'LoginAssetConfirmStatusAPI']


class LoginAssetCheckAPI(CreateAPIView):
    permission_classes = (IsAppUser, )
    serializer_class = serializers.LoginAssetCheckSerializer

    @lazyproperty
    def serializer(self):
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        return serializer

    def create(self, request, *args, **kwargs):
        need_confirm, data = self.check_confirm()
        return Response(data=data, status=200)

    def check_confirm(self):
        with tmp_to_org(self.serializer.org):
            quires = {
                'user': self.serializer.user, 'asset': self.serializer.asset,
                'system_user': self.serializer.system_user,
                'action': LoginAssetACL.ActionChoices.login_confirm
            }
            acl = LoginAssetACL.filter(**quires).first()

        if not acl:
            need_confirm = False
            data = {}
        else:
            need_confirm = True
            ticket = LoginAssetACL.create_login_asset_confirm_ticket(
                user=self.serializer.user,
                asset=self.serializer.asset,
                system_user=self.serializer.system_user,
                assignees=acl.reviewers.all(),
                org_id=self.serializer.org.id
            )
            confirm_status_url = reverse(
                view_name='acls:login-asset-confirm-status',
                kwargs={'pk': str(ticket.id)}
            )
            ticket_detail_url = reverse(
                view_name='api-tickets:ticket-detail',
                kwargs={'pk': str(ticket.id)},
                external=True, api_to_ui=True
            )
            ticket_detail_url = '{url}?type={type}'.format(url=ticket_detail_url, type=ticket.type)
            data = {
                'check_confirm_status': {'method': 'GET', 'url': confirm_status_url},
                'close_confirm': {'method': 'DELETE', 'url': confirm_status_url},
                'ticket_detail_url': ticket_detail_url,
                'reviewers': [str(user) for user in ticket.assignees.all()],
            }

        data.update({
            'need_confirm': need_confirm
        })
        return need_confirm, data


class LoginAssetConfirmStatusAPI(RetrieveDestroyAPIView):
    permission_classes = (IsAppUser, )

    @lazyproperty
    def ticket(self):
        with tmp_to_root_org():
            return get_object_or_404(Ticket, pk=self.kwargs['pk'])

    def retrieve(self, request, *args, **kwargs):
        if self.ticket.action_open:
            status = 'await'
        elif self.ticket.action_approve:
            status = 'approve'
        else:
            status = 'reject'
        data = {
            'status': status,
            'action': self.ticket.action,
            'processor': self.ticket.processor_display
        }
        return Response(data=data, status=200)

    def destroy(self, request, *args, **kwargs):
        if self.ticket.status_open:
            self.ticket.close(processor=self.ticket.applicant)
        data = {
            'action': self.ticket.action,
            'status': self.ticket.status,
            'processor': self.ticket.processor_display
        }
        return Response(data=data, status=200)
