from collections import namedtuple

from django.db.transaction import atomic
from django.db.models import F
from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from users.models.user import User
from common.const.http import POST, GET
from common.drf.api import JMSModelViewSet
from common.permissions import IsValidUser
from common.utils.django import get_object_or_none
from common.drf.serializers import EmptySerializer
from perms.models.asset_permission import AssetPermission, Asset
from assets.models.user import SystemUser
from ..exceptions import (
    ConfirmedAssetsChanged, ConfirmedSystemUserChanged,
    TicketClosed, TicketActionYet, NotHaveConfirmedAssets,
    NotHaveConfirmedSystemUser
)
from .. import serializers
from ..models import Ticket
from ..permissions import IsAssignee


class RequestAssetPermTicketViewSet(JMSModelViewSet):
    queryset = Ticket.objects.filter(type=Ticket.TYPE_REQUEST_ASSET_PERM)
    serializer_classes = {
        'default': serializers.RequestAssetPermTicketSerializer,
        'approve': EmptySerializer,
        'reject': EmptySerializer,
        'assignees': serializers.OrgAssigneeSerializer,
    }
    permission_classes = (IsValidUser,)
    filter_fields = ['status', 'title', 'action', 'user_display']
    search_fields = ['user_display', 'title']

    def _check_can_set_action(self, instance, action):
        if instance.status == instance.STATUS_CLOSED:
            raise TicketClosed(detail=_('Ticket closed'))
        if instance.action == action:
            action_display = dict(instance.ACTION_CHOICES).get(action)
            raise TicketActionYet(detail=_('Ticket has %s') % action_display)

    @action(detail=False, methods=[GET], permission_classes=[IsValidUser])
    def assignees(self, request, *args, **kwargs):
        org_mapper = {}
        UserTuple = namedtuple('UserTuple', ('id', 'name', 'username'))
        user = request.user
        superusers = User.objects.filter(role=User.ROLE_ADMIN)

        admins_with_org = User.objects.filter(related_admin_orgs__users=user).annotate(
            org_id=F('related_admin_orgs__id'), org_name=F('related_admin_orgs__name')
        )

        for user in admins_with_org:
            org_id = user.org_id

            if org_id not in org_mapper:
                org_mapper[org_id] = {
                    'org_name': user.org_name,
                    'org_admins': set()  # 去重
                }
            org_mapper[org_id]['org_admins'].add(UserTuple(user.id, user.name, user.username))

        result = [
            {
                'org_name': _('Superuser'),
                'org_admins': set(UserTuple(user.id, user.name, user.username)
                                  for user in superusers)
            }
        ]

        for org in org_mapper.values():
            result.append(org)
        serializer_class = self.get_serializer_class()
        serilizer = serializer_class(instance=result, many=True)
        return Response(data=serilizer.data)

    @action(detail=True, methods=[POST], permission_classes=[IsAssignee, IsValidUser])
    def reject(self, request, *args, **kwargs):
        instance = self.get_object()
        action = instance.ACTION_REJECT
        self._check_can_set_action(instance, action)
        instance.perform_action(action, request.user)
        return Response()

    @action(detail=True, methods=[POST], permission_classes=[IsAssignee, IsValidUser])
    def approve(self, request, *args, **kwargs):
        instance = self.get_object()
        action = instance.ACTION_APPROVE
        self._check_can_set_action(instance, action)

        meta = instance.meta
        confirmed_assets = meta.get('confirmed_assets', [])
        assets = list(Asset.objects.filter(id__in=confirmed_assets))
        if not assets:
            raise NotHaveConfirmedAssets(detail=_('Confirm assets first'))

        if len(assets) != len(confirmed_assets):
            raise ConfirmedAssetsChanged(detail=_('Confirmed assets changed'))

        confirmed_system_user = meta.get('confirmed_system_user')
        if not confirmed_system_user:
            raise NotHaveConfirmedSystemUser(detail=_('Confirm system-user first'))

        system_user = get_object_or_none(SystemUser, id=confirmed_system_user)
        if system_user is None:
            raise ConfirmedSystemUserChanged(detail=_('Confirmed system-user changed'))

        self._create_asset_permission(instance, assets, system_user)
        return Response({'detail': _('Succeed')})

    def _create_asset_permission(self, instance: Ticket, assets, system_user):
        meta = instance.meta
        request = self.request
        ap_kwargs = {
            'name': meta.get('name', ''),
            'created_by': self.request.user.username,
            'comment': _('{} request assets, approved by {}').format(instance.user_display,
                                                                  instance.assignee_display)
        }
        date_start = meta.get('date_start')
        date_expired = meta.get('date_expired')
        if date_start:
            ap_kwargs['date_start'] = date_start
        if date_expired:
            ap_kwargs['date_expired'] = date_expired

        with atomic():
            instance.perform_action(instance.ACTION_APPROVE, request.user)
            ap = AssetPermission.objects.create(**ap_kwargs)
            ap.system_users.add(system_user)
            ap.assets.add(*assets)

        return ap
