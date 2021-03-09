from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, RetrieveDestroyAPIView

from common.permissions import IsAppUser
from common.utils import reverse, lazyproperty
from tickets.models import Ticket
from orgs.utils import tmp_to_root_org
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
        need, data = self.check_confirm()
        return Response(data=data, status=200)

    def check_confirm(self):
        acl = LoginAssetACL.filter(
            self.serializer.user, self.serializer.asset, self.serializer.system_user,
            self.serializer.org.id
        ).first()

        if not acl:
            need = False
            data = {'need_confirm': False}
            return need, data

        need = True
        reviewers = acl.reviewers.all()
        ticket = LoginAssetACL.create_login_asset_confirm_ticket(
            self.serializer.user, self.serializer.asset, self.serializer.system_user, reviewers,
            self.serializer.org.id
        )
        confirm_status_url = reverse(
            'acls:login-asset-confirm-status', kwargs={'pk': str(ticket.id)}
        )
        ticket_detail_url = reverse(
            'api-tickets:ticket-detail', kwargs={'pk': str(ticket.id)}, external=True,
            api_to_ui=True
        )
        ticket_detail_url = '{url}?type={type}'.format(url=ticket_detail_url, type=ticket.type)
        data = {
            'need_confirm': True,
            'check_confirm_status': {'method': 'GET', 'url': confirm_status_url},
            'close_confirm': {'method': 'DELETE', 'url': confirm_status_url},
            'ticket_detail_url': ticket_detail_url,
            'reviewers': [str(user) for user in ticket.assignees.all()],
        }
        return need, data


class LoginAssetConfirmStatusAPI(RetrieveDestroyAPIView):
    permission_classes = (IsAppUser, )

    def get_ticket(self):
        with tmp_to_root_org():
            return get_object_or_404(Ticket, pk=self.kwargs['pk'])

    def retrieve(self, request, *args, **kwargs):
        ticket = self.get_ticket()
        if ticket.action_open:
            status = 'await'
        elif ticket.action_approve:
            status = 'approve'
        else:
            status = 'reject'
        data = {
            'status': status,
            'action': ticket.action,
            'processor': ticket.processor_display
        }
        return Response(data=data, status=200)

    def destroy(self, request, *args, **kwargs):
        ticket = self.get_ticket()
        ticket.close(processor=ticket.applicant)
        data = {
            'action': ticket.action,
            'status': ticket.status,
            'processor': ticket.processor_display
        }
        return Response(data=data, status=200)
