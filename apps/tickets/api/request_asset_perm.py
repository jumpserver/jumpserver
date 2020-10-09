import textwrap

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request

from orgs.models import Organization, ROLE as ORG_ROLE
from users.models.user import User
from common.const.http import POST, GET
from common.drf.api import JMSModelViewSet
from common.permissions import IsValidUser, IsObjectOwner
from common.utils.django import get_object_or_none
from common.utils.timezone import dt_parser
from common.drf.serializers import EmptySerializer
from perms.models.asset_permission import AssetPermission, Asset
from perms.models import Action
from assets.models.user import SystemUser
from ..exceptions import (
    ConfirmedAssetsChanged, ConfirmedSystemUserChanged,
    TicketClosed, TicketActionAlready, NotHaveConfirmedAssets,
    NotHaveConfirmedSystemUser
)
from .. import serializers
from ..models import Ticket
from ..permissions import IsAssignee


class RequestAssetPermTicketViewSet(JMSModelViewSet):
    queryset = Ticket.origin_objects.filter(type=Ticket.TYPE.REQUEST_ASSET_PERM)
    serializer_classes = {
        'default': serializers.RequestAssetPermTicketSerializer,
        'approve': EmptySerializer,
        'reject': EmptySerializer,
        'close': EmptySerializer,
        'assignees': serializers.AssigneeSerializer,
    }
    permission_classes = (IsValidUser,)
    filter_fields = ['status', 'title', 'action', 'user_display', 'org_id']
    search_fields = ['user_display', 'title']

    def _check_can_set_action(self, instance, action):
        if instance.status == instance.STATUS.CLOSED:
            raise TicketClosed
        if instance.action == action:
            action_display = instance.ACTION.get(action)
            raise TicketActionAlready(detail=_('Ticket has %s') % action_display)

    @action(detail=False, methods=[GET], permission_classes=[IsValidUser])
    def assignees(self, request: Request, *args, **kwargs):
        user = request.user
        org_id = request.query_params.get('org_id', Organization.DEFAULT_ID)

        q = Q(role=User.ROLE.ADMIN)
        if org_id != Organization.DEFAULT_ID:
            q |= Q(m2m_org_members__role=ORG_ROLE.ADMIN, orgs__id=org_id, orgs__members=user)
        org_admins = User.objects.filter(q).distinct()

        return self.get_paginated_response_with_query_set(org_admins)

    def _get_extra_comment(self, instance):
        meta = instance.meta
        ips = ', '.join(meta.get('ips', []))
        confirmed_assets = ', '.join(meta.get('confirmed_assets', []))
        confirmed_system_users = ', '.join(meta.get('confirmed_system_users', []))

        return textwrap.dedent(f'''\
            {_('IP group')}: {ips}
            {_('Hostname')}: {meta.get('hostname', '')}
            {_('System user')}: {meta.get('system_user', '')}
            {_('Confirmed assets')}: {confirmed_assets}
            {_('Confirmed system users')}: {confirmed_system_users}
        ''')

    @action(detail=True, methods=[POST], permission_classes=[IsAssignee, IsValidUser])
    def reject(self, request, *args, **kwargs):
        instance = self.get_object()
        action = instance.ACTION.REJECT
        self._check_can_set_action(instance, action)
        instance.perform_action(action, request.user, self._get_extra_comment(instance))
        return Response()

    @action(detail=True, methods=[POST], permission_classes=[IsAssignee, IsValidUser])
    def approve(self, request, *args, **kwargs):
        instance = self.get_object()
        action = instance.ACTION.APPROVE
        self._check_can_set_action(instance, action)

        meta = instance.meta
        confirmed_assets = meta.get('confirmed_assets', [])
        assets = list(Asset.objects.filter(id__in=confirmed_assets))
        if not assets:
            raise NotHaveConfirmedAssets(detail=_('Confirm assets first'))

        if len(assets) != len(confirmed_assets):
            raise ConfirmedAssetsChanged(detail=_('Confirmed assets changed'))

        confirmed_system_users = meta.get('confirmed_system_users', [])
        if not confirmed_system_users:
            raise NotHaveConfirmedSystemUser(detail=_('Confirm system-users first'))

        system_users = SystemUser.objects.filter(id__in=confirmed_system_users)
        if system_users is None:
            raise ConfirmedSystemUserChanged(detail=_('Confirmed system-users changed'))

        self._create_asset_permission(instance, assets, system_users)
        return Response({'detail': _('Succeed')})

    @action(detail=True, methods=[POST], permission_classes=[IsAssignee | IsObjectOwner])
    def close(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.status = Ticket.STATUS.CLOSED
        instance.save()
        return Response({'detail': _('Succeed')})

    def _create_asset_permission(self, instance: Ticket, assets, system_users):
        meta = instance.meta
        request = self.request
        actions = meta.get('actions', Action.CONNECT)

        ap_kwargs = {
            'name': _('From request ticket: {} {}').format(instance.user_display, instance.id),
            'created_by': self.request.user.username,
            'comment': _('{} request assets, approved by {}').format(instance.user_display,
                                                                     instance.assignees_display),
            'actions': actions,
        }
        date_start = dt_parser(meta.get('date_start'))
        date_expired = dt_parser(meta.get('date_expired'))
        if date_start:
            ap_kwargs['date_start'] = date_start
        if date_expired:
            ap_kwargs['date_expired'] = date_expired
        instance.perform_action(instance.ACTION.APPROVE,
                                request.user,
                                self._get_extra_comment(instance))
        ap = AssetPermission.objects.create(**ap_kwargs)
        ap.system_users.add(*system_users)
        ap.assets.add(*assets)
        ap.users.add(instance.user)

        return ap
