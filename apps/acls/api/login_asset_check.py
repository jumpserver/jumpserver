from django.utils.translation import gettext_lazy as _
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response

from common.exceptions import JMSException
from common.utils import lazyproperty, get_request_ip_or_data
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
        data = self.check_review()
        return Response(data=data, status=200)

    @lazyproperty
    def serializer(self):
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        return serializer

    def check_review(self):
        user = self.serializer.user
        asset = self.serializer.asset

        account_username = self.serializer.validated_data.get('account_username')
        queryset = LoginAssetACL.filter_queryset(
            user=user, asset=asset, account_username=account_username,
        )
        acl = LoginAssetACL.get_match_rule_acls(
            user, get_request_ip_or_data(self.request), queryset,
        )
        if acl and acl.is_action(acl.ActionChoices.reject):
            raise JMSException(
                code='acl_reject', detail=_('ACL action is reject: {}({})').format(acl.name, acl.id),
            )

        reviews = acl.pending_reviews(user, asset, account_username) if acl else ()
        return {
            'need_review': bool(reviews),
            'requirements': [
                field.removesuffix('_enabled') for field in LoginAssetACL.CONTROL_FIELDS
                if acl and acl.enabled(field)
            ],
        }
