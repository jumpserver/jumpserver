# -*- coding: utf-8 -*-

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import Response

from authentication.mapping import MISSING, AuthMappingService
from common.drf.filters import IDSpmFilterBackend
from common.utils import get_logger
from orgs.models import Organization
from orgs.utils import tmp_to_root_org
from rbac.builtin import BuiltinRole
from rbac.const import Scope
from rbac.models import Role
from rbac.permissions import RBACPermission
from users.models import User, UserGroup
from ..const import ImportStatus
from ..models import Setting
from ..serializers import LDAPUserSerializer
from ..utils import (
    LDAPServerUtil, LDAPCacheUtil, LDAPImportUtil,
    LDAP_USE_CACHE_FLAGS
)

logger = get_logger(__file__)


class LDAPMappingOptionPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 100


class LDAPMappingOptionApi(generics.GenericAPIView):
    permission_classes = (IsAuthenticated, RBACPermission)
    perm_model = Setting
    rbac_perms = {'GET': 'settings.change_auth'}
    pagination_class = LDAPMappingOptionPagination
    option_types = {'user_group', 'organization', 'system_role', 'org_role'}

    def get(self, request):
        option_type = request.query_params.get('type', '')
        if option_type not in self.option_types:
            raise ValidationError({
                'type': _('Unsupported LDAP mapping option type')
            })
        search = (
            request.query_params.get('q') or
            request.query_params.get('search', '')
        ).strip()
        with tmp_to_root_org():
            queryset = self.get_options_queryset(option_type, search)
            queryset = IDSpmFilterBackend().filter_queryset(
                request, queryset, self
            )
            objects = self.paginate_queryset(queryset)
            results = self.serialize_options(option_type, objects)
        return self.get_paginated_response(results)

    @staticmethod
    def get_options_queryset(option_type, search):
        if option_type == 'user_group':
            queryset = UserGroup.objects.exclude(
                org_id=Organization.SYSTEM_ID
            )
        elif option_type == 'organization':
            queryset = Organization.objects.exclude(id=Organization.SYSTEM_ID)
        else:
            scope = Scope.system if option_type == 'system_role' else Scope.org
            queryset = Role.objects.filter(scope=scope)
            if scope == Scope.system:
                queryset = queryset.exclude(id=BuiltinRole.system_component.id)
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset.order_by('name', 'id')

    @staticmethod
    def serialize_options(option_type, objects):
        if option_type == 'user_group':
            org_ids = {obj.org_id for obj in objects}
            org_names = {
                str(org.id): org.name
                for org in Organization.objects.filter(id__in=org_ids)
            }
            org_names[Organization.ROOT_ID] = str(Organization.ROOT_NAME)
            return [{
                'id': str(obj.id),
                'label': '{} / {}'.format(
                    org_names.get(str(obj.org_id), ''), obj.name
                ),
                'org_id': str(obj.org_id),
            } for obj in objects]
        if option_type == 'organization':
            return [{
                'id': str(obj.id),
                'label': obj.name,
            } for obj in objects]
        return [{
            'id': str(obj.id),
            'label': str(obj.display_name),
        } for obj in objects]


class LDAPUserListApi(generics.ListAPIView):
    serializer_class = LDAPUserSerializer
    perm_model = Setting
    rbac_perms = {
        'list': 'settings.change_auth'
    }

    def get_serializer(self, *args, **kwargs):
        instances = args[0] if args else kwargs.get('instance')
        if kwargs.get('many') and instances is not None:
            context = kwargs.setdefault('context', self.get_serializer_context())
            context['ldap_mapping_previews'] = self.get_mapping_previews(instances)
        return super().get_serializer(*args, **kwargs)

    def get_mapping_previews(self, users):
        users = list(users)
        category = self.request.query_params.get('category')
        previews = {
            id(user): self.empty_mapping_preview(
                user.get('_auth_mapping_error', '')
            )
            for user in users
        }
        if category not in (User.Source.ldap.value, User.Source.ldap_ha.value):
            return previews

        group_rules = []
        resolved = [
            {'groups': [], 'roles': [], 'error': ''} for _ in users
        ]
        if category == User.Source.ldap.value:
            group_rules = getattr(settings, 'AUTH_LDAP_USER_GROUP_MAP', [])
            service = AuthMappingService(
                source=category,
                group_rules=group_rules,
                role_rules=getattr(settings, 'AUTH_LDAP_USER_ROLE_MAP', []),
            )
            records = [
                (
                    user.get('_auth_attributes', MISSING),
                    user.get('groups', MISSING),
                )
                for user in users
            ]
            resolved = service.preview_many(records)

        legacy = LDAPImportUtil(category=category)
        for user, preview in zip(users, resolved):
            if user.get('_auth_mapping_error'):
                continue
            if preview.get('error'):
                previews[id(user)] = self.empty_mapping_preview(
                    preview['error']
                )
                continue
            try:
                if group_rules:
                    mapped_groups = self.format_mapped_groups(preview)
                else:
                    groups = user.get('groups', MISSING)
                    mapped_groups = [] if groups is MISSING else (
                        legacy.get_user_group_names(groups)
                    )
                previews[id(user)] = {
                    'mapped_groups': mapped_groups,
                    'mapped_roles': self.format_mapped_roles(preview),
                    'error': '',
                }
            except Exception as error:
                previews[id(user)] = self.empty_mapping_preview(str(error))
        return previews

    @staticmethod
    def empty_mapping_preview(error=''):
        return {
            'mapped_groups': [], 'mapped_roles': [], 'error': error,
        }

    @staticmethod
    def format_mapped_groups(preview):
        org_names = {
            str(org.id): str(org.name)
            for _, org in preview['roles'] if org is not None
        }
        org_names[Organization.ROOT_ID] = str(Organization.ROOT_NAME)
        return [
            '{} / {}'.format(
                org_names.get(str(group.org_id), ''), group.name
            )
            for group in preview['groups']
        ]

    @staticmethod
    def format_mapped_roles(preview):
        labels = []
        for role, org in preview['roles']:
            role_name = str(role.display_name)
            if org is not None:
                role_name = f'{org.name} / {role_name}'
            labels.append(role_name)
        return labels

    def get_queryset_from_cache(self):
        search_value = self.request.query_params.get('search')
        category = self.request.query_params.get('category')
        users = LDAPCacheUtil(category=category).search(search_value=search_value)
        return users

    def get_queryset_from_server(self):
        search_value = self.request.query_params.get('search')
        category = self.request.query_params.get('category')
        users = LDAPServerUtil(category=category).search(search_value=search_value)
        return users

    def get_queryset(self):
        if hasattr(self, 'swagger_fake_view'):
            return User.objects.none()
        cache_police = self.request.query_params.get('cache_police', True)
        if cache_police in LDAP_USE_CACHE_FLAGS:
            users = self.get_queryset_from_cache()
        else:
            users = self.get_queryset_from_server()
        return users

    @staticmethod
    def processing_queryset(queryset):
        db_username_list = User.objects.all().values_list('username', flat=True)
        for q in queryset:
            q['id'] = q['username']
            q['existing'] = q['username'] in db_username_list
        return queryset

    def sort_queryset(self, queryset):
        order_by = self.request.query_params.get('order')
        if not order_by:
            order_by = 'existing'
        if order_by.startswith('-'):
            order_by = order_by.lstrip('-')
            reverse = True
        else:
            reverse = False
        queryset = sorted(queryset, key=lambda x: x[order_by], reverse=reverse)
        return queryset

    def filter_queryset(self, queryset):
        if queryset is None:
            return queryset
        queryset = self.processing_queryset(queryset)
        queryset = self.sort_queryset(queryset)
        return queryset

    def list(self, request, *args, **kwargs):
        cache_police = self.request.query_params.get('cache_police', True)
        # 不是用缓存
        if cache_police not in LDAP_USE_CACHE_FLAGS:
            return super().list(request, *args, **kwargs)

        try:
            queryset = self.get_queryset()
        except Exception as e:
            data = {'error': str(e)}
            return Response(data=data, status=400)

        # 缓存有数据
        if queryset is not None:
            return super().list(request, *args, **kwargs)
        else:
            data = {'msg': _('Users are not synchronized, please click the user synchronization button')}
            return Response(data=data, status=400)
