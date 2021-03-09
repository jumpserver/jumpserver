from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, RetrieveDestroyAPIView

from common.permissions import IsAppUser
from common.utils import reverse
from tickets.models import Ticket
from orgs.utils import tmp_to_root_org
from ..models import LoginAssetACL
from .. import serializers


__all__ = ['LoginAssetConfirmCheckAPI', 'LoginAssetConfirmStatusAPI']


class LoginAssetConfirmCheckAPI(CreateAPIView):
    # permission_classes = (IsAppUser, )
    serializer_class = serializers.LoginAssetConfirmCheckSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        queryset = self.get_acl_queryset(serializer)
        if not queryset:
            data = {'need_confirm': False}
            return Response(data=data, status=200)

        reviewers = LoginAssetACL.get_reviewers(queryset)
        ticket = self.create_ticket(serializer, reviewers)
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
        return Response(data=data, status=200)

    @staticmethod
    def get_acl_queryset(serializer):
        queryset = LoginAssetACL.filter(serializer.user, serializer.asset, serializer.system_user)
        return queryset

    @staticmethod
    def create_ticket(serializer, reviewers):
        ticket = LoginAssetACL.create_login_asset_confirm_ticket(
            serializer.user, serializer.asset, serializer.system_user, assignees=reviewers
        )
        return ticket


class LoginAssetConfirmStatusAPI(RetrieveDestroyAPIView):
    # permission_classes = (IsAppUser, )

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
