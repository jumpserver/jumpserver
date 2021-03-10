from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, RetrieveDestroyAPIView

from common.permissions import IsAppUser
from common.utils import reverse, lazyproperty
from orgs.utils import tmp_to_org
from ..models import LoginAssetACL
from .. import serializers


__all__ = ['LoginAssetCheckAPI', 'LoginAssetConfirmStatusAPI']


class LoginAssetCheckAPI(CreateAPIView):
    permission_classes = (IsAppUser, )
    serializer_class = serializers.LoginAssetCheckSerializer

    def create(self, request, *args, **kwargs):
        is_need_confirm, response_data = self.check_if_need_confirm()
        return Response(data=response_data, status=200)

    def check_if_need_confirm(self):
        quires = {
            'user': self.serializer.user, 'asset': self.serializer.asset,
            'system_user': self.serializer.system_user,
            'action': LoginAssetACL.ActionChoices.login_confirm
        }
        with tmp_to_org(self.serializer.org):
            acl = LoginAssetACL.filter(**quires).valid().first()

        if not acl:
            is_need_confirm = False
            response_data = {}
        else:
            is_need_confirm = True
            response_data = self._get_response_data_of_need_confirm(acl)
        response_data['need_confirm'] = is_need_confirm
        return is_need_confirm, response_data

    def _get_response_data_of_need_confirm(self, acl):
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
        return data

    @lazyproperty
    def serializer(self):
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        return serializer


class LoginAssetConfirmStatusAPI(RetrieveDestroyAPIView):
    permission_classes = (IsAppUser, )

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

    @lazyproperty
    def serializer(self):
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        return serializer

