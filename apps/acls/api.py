from django.db.models import QuerySet
from django.utils import timezone
from orgs.mixins.api import OrgModelViewSet
from common.permissions import IsOrgAdminOrAppUser
from rest_framework.views import APIView, Response
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from assets.models import Asset, SystemUser
from users.models import User
from tickets.models import Ticket
from tickets import const

from .models import AssetACLPolicy
from .utils import get_acl_policies_by_user_asset_sys
from .serializers import (AssetACLPolicySerializer,
                          ValidateAssetACLSerializer,
                          ValidateCancelConfirmSerializer)


class AssetACLViewSet(OrgModelViewSet):
    permission_classes = (IsOrgAdminOrAppUser,)
    model = AssetACLPolicy
    filterset_fields = ("name", 'user', 'ip', 'port', 'system_user')
    search_fields = filterset_fields
    serializer_class = AssetACLPolicySerializer


class ValidateAssetLoginConfirmApi(APIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    def open_ticket_or_not(self, validated_data):
        user_id = validated_data.get('user_id')
        asset_id = validated_data.get('asset_id')
        system_id = validated_data.get('system_user_id')
        system_username = validated_data.get("system_username")
        asset = get_object_or_404(Asset, id=asset_id)
        sys = get_object_or_404(SystemUser, id=system_id)
        user = get_object_or_404(User, id=user_id)
        asset_acl_policies = get_acl_policies_by_user_asset_sys(user, asset, sys, system_username)
        if not asset_acl_policies:
            return None
        reviewers = self.get_policies_reviewers(asset_acl_policies)
        ticket_title = _('Asset Login confirm') + ' {}'.format(user.username)
        ticket_meta = self.construct_confirm_ticket_meta(asset, system_username)
        data = {
            'title': ticket_title,
            'type': const.TicketTypeChoices.asset_login_confirm.value,
            'meta': ticket_meta,
        }
        ticket = Ticket.objects.create(**data)
        ticket.assignees.set(reviewers)
        ticket.open(user)
        return ticket

    def get_policies_reviewers(self, asset_acl_policies: QuerySet(AssetACLPolicy)):
        reviewers = set()
        for acl_item in asset_acl_policies.all():
            for reviewer in acl_item.reviewers.all():
                reviewers.add(reviewer)
        return reviewers

    def get(self, request, *args, **kwargs):
        serializer = ValidateAssetACLSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        ticket = self.open_ticket_or_not(serializer.validated_data)
        if not ticket:
            return Response({'msg': True})
        return Response({'msg': False, 'error': _("Asset Login Confirm"), 'ticket_id': ticket.id})

    def delete(self, request, *args, **kwargs):
        serializer = ValidateCancelConfirmSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        self.close_asset_login_confirm_ticket(serializer.validated_data)
        return Response('', status=200)

    def close_asset_login_confirm_ticket(self, validated_data):
        ticket_id = validated_data.get("ticket_id")
        user_id = validated_data.get("user_id")
        user = get_object_or_404(User, id=user_id)
        ticket = get_object_or_404(Ticket, id=ticket_id)
        ticket.close(processor=user)

    def construct_confirm_ticket_meta(self, asset: Asset, sys_username):
        login_datetime = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        ticket_meta = {
            'apply_login_asset_ip': asset.ip,
            'apply_sys_username': sys_username,
            'apply_login_datetime': login_datetime,
        }
        return ticket_meta
