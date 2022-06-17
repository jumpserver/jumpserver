from rest_framework.response import Response
from rest_framework.generics import CreateAPIView

from common.utils import reverse, lazyproperty
from orgs.utils import tmp_to_org
from ..models import LoginAssetACL
from .. import serializers

__all__ = ['LoginAssetCheckAPI']


class LoginAssetCheckAPI(CreateAPIView):
    serializer_class = serializers.LoginAssetCheckSerializer
    model = LoginAssetACL
    rbac_perms = {
        'POST': 'tickets.add_superticket'
    }

    def get_queryset(self):
        return LoginAssetACL.objects.all()

    def create(self, request, *args, **kwargs):
        is_need_confirm, response_data = self.check_if_need_confirm()
        return Response(data=response_data, status=200)

    def check_if_need_confirm(self):
        queries = {
            'user': self.serializer.user, 'asset': self.serializer.asset,
            'system_user': self.serializer.system_user,
            'action': LoginAssetACL.ActionChoices.login_confirm
        }
        with tmp_to_org(self.serializer.org):
            acl = LoginAssetACL.filter(**queries).valid().first()

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
            org_id=self.serializer.org.id,
        )
        confirm_status_url = reverse(
            view_name='api-tickets:super-ticket-status',
            kwargs={'pk': str(ticket.id)}
        )
        ticket_detail_url = reverse(
            view_name='api-tickets:ticket-detail',
            kwargs={'pk': str(ticket.id)},
            external=True, api_to_ui=True
        )
        ticket_detail_url = '{url}?type={type}'.format(url=ticket_detail_url, type=ticket.type)
        ticket_assignees = ticket.current_step.ticket_assignees.all()
        data = {
            'check_confirm_status': {'method': 'GET', 'url': confirm_status_url},
            'close_confirm': {'method': 'DELETE', 'url': confirm_status_url},
            'ticket_detail_url': ticket_detail_url,
            'reviewers': [str(ticket_assignee.assignee) for ticket_assignee in ticket_assignees],
            'ticket_id': str(ticket.id)
        }
        return data

    @lazyproperty
    def serializer(self):
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        return serializer

