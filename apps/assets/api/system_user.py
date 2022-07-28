# ~*~ coding: utf-8 ~*~
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet

from common.utils import get_logger, get_object_or_none
from common.mixins.api import SuggestionMixin
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.mixins import generics
from ..models import SystemUser, CommandFilterRule, Account
from .. import serializers

logger = get_logger(__file__)
__all__ = [
    'SystemUserViewSet', 'SystemUserAuthInfoApi',
    'SystemUserCommandFilterRuleListApi',
    'SystemUserAssetAccountApi',
    'SystemUserAssetAccountSecretApi',
]


class SystemUserViewSet(SuggestionMixin, OrgBulkModelViewSet):
    """
    System user api set, for add,delete,update,list,retrieve resource
    """
    model = SystemUser
    filterset_fields = {
        'name': ['exact'],
        'username': ['exact'],
        'protocol': ['exact', 'in'],
    }
    search_fields = filterset_fields
    serializer_class = serializers.SystemUserSerializer
    serializer_classes = {
        'default': serializers.SystemUserSerializer,
        'suggestion': serializers.MiniSystemUserSerializer
    }
    ordering_fields = ('name', 'protocol', 'login_mode')
    ordering = ('name', )
    rbac_perms = {
        'su_from': 'assets.view_systemuser',
        'su_to': 'assets.view_systemuser',
        'match': 'assets.match_systemuser'
    }

    @action(methods=['get'], detail=False, url_path='su-from')
    def su_from(self, request, *args, **kwargs):
        """ API 获取可选的 su_from 系统用户"""
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.filter(
            protocol=SystemUser.Protocol.ssh, login_mode=SystemUser.LOGIN_AUTO
        )
        return self.get_paginate_response_if_need(queryset)

    @action(methods=['get'], detail=True, url_path='su-to')
    def su_to(self, request, *args, **kwargs):
        """ 获取系统用户的所有 su_to 系统用户 """
        pk = kwargs.get('pk')
        system_user = get_object_or_404(SystemUser, pk=pk)
        queryset = system_user.su_to.all()
        queryset = self.filter_queryset(queryset)
        return self.get_paginate_response_if_need(queryset)

    def get_paginate_response_if_need(self, queryset):
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class SystemUserAccountViewSet(GenericViewSet):
    model = Account
    serializer_classes = {
        'default': serializers.AccountSerializer,
        'account_secret': serializers.AccountSecretSerializer,
    }

    def get_object(self):
        system_user_id = self.kwargs.get('pk')
        asset_id = self.kwargs.get('asset_id')
        user_id = self.kwargs.get("user_id")
        system_user = SystemUser.objects.get(id=system_user_id)
        account = system_user.get_account(user_id, asset_id)
        return account

    @action(methods=['get'], detail=False, url_path='account')
    def account(self, request, *args, **kwargs):
        pass

    @action(methods=['get'], detail=False, url_path='account-secret')
    def account_secret(self):
        pass

    @action(methods=['put'], detail=False, url_path='manual-account')
    def manual_account(self, request, *args, **kwargs):
        pass


class SystemUserAssetAccountApi(generics.RetrieveAPIView):
    model = Account
    serializer_class = serializers.AccountSerializer

    def get_object(self):
        system_user_id = self.kwargs.get('pk')
        asset_id = self.kwargs.get('asset_id')
        user_id = self.kwargs.get("user_id")
        system_user = SystemUser.objects.get(id=system_user_id)
        account = system_user.get_account(user_id, asset_id)
        return account


class SystemUserAssetAccountSecretApi(SystemUserAssetAccountApi):
    model = Account
    serializer_class = serializers.AccountSecretSerializer
    rbac_perms = {
        'retrieve': 'assets.view_accountsecret'
    }


class SystemUserAuthInfoApi(generics.RetrieveUpdateDestroyAPIView):
    """
    Get system user auth info
    """
    model = SystemUser
    serializer_class = serializers.AccountSerializer
    rbac_perms = {
        'retrieve': 'assets.view_systemusersecret',
        'list': 'assets.view_systemusersecret',
        'change': 'assets.change_systemuser',
        'destroy': 'assets.change_systemuser',
    }

    def get_object(self):
        system_user_id = self.kwargs.get('pk')
        asset_id = self.kwargs.get('asset_id')
        user_id = self.kwargs.get("user_id")
        system_user = SystemUser.objects.get(id=system_user_id)
        account = system_user.get_account(user_id, asset_id)
        return account

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.clear_auth()
        return Response(status=204)


class SystemUserCommandFilterRuleListApi(generics.ListAPIView):
    rbac_perms = {
        'list': 'assets.view_commandfilterule'
    }

    def get_serializer_class(self):
        from ..serializers import CommandFilterRuleSerializer
        return CommandFilterRuleSerializer

    def get_queryset(self):
        user_id = self.request.query_params.get('user_id')
        user_group_id = self.request.query_params.get('user_group_id')
        system_user_id = self.kwargs.get('pk', None)
        system_user = get_object_or_none(SystemUser, pk=system_user_id)
        if not system_user:
            system_user_id = self.request.query_params.get('system_user_id')
        asset_id = self.request.query_params.get('asset_id')
        application_id = self.request.query_params.get('application_id')
        rules = CommandFilterRule.get_queryset(
            user_id=user_id,
            user_group_id=user_group_id,
            system_user_id=system_user_id,
            asset_id=asset_id,
            application_id=application_id
        )
        return rules

