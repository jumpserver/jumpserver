from rest_framework.generics import CreateAPIView
from rest_framework.response import Response

from common.utils import reverse, lazyproperty
from orgs.utils import tmp_to_org
from .. import serializers
from ..models import LoginAssetACL

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
        data = self.check_confirm()
        return Response(data=data, status=200)

    @lazyproperty
    def serializer(self):
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        return serializer

    def check_confirm(self):
        with tmp_to_org(self.serializer.asset.org):
            acl = LoginAssetACL.objects \
                .filter(action=LoginAssetACL.ActionChoices.review) \
                .filter_user(self.serializer.user) \
                .filter_asset(self.serializer.asset) \
                .filter_account(self.serializer.validated_data.get('account_username')) \
                .valid() \
                .first()
        if acl:
            need_confirm = True
            response_data = self._get_response_data_of_need_confirm(acl)
        else:
            need_confirm = False
            response_data = {}
        response_data['need_confirm'] = need_confirm
        return response_data

    def _get_response_data_of_need_confirm(self, acl) -> dict:
        ticket = LoginAssetACL.create_login_asset_confirm_ticket(
            user=self.serializer.user,
            asset=self.serializer.asset,
            account_username=self.serializer.validated_data.get('account_username'),
            assignees=acl.reviewers.all(),
            org_id=self.serializer.asset.org.id,
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
