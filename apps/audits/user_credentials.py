from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404
from django.utils.crypto import salted_hmac
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.metadata import SimpleMetadata
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from authentication.backends.passkey.models import Passkey
from authentication.models import AccessKey, PrivateToken, SSHKey
from common.drf.filters import IDSpmFilterBackend, SearchFilter
from common.drf.renders import CSVFileRenderer, ExcelFileRenderer
from common.permissions import IsValidUser
from common.utils import is_uuid
from rbac.permissions import RBACPermission
from users.models import User


CREDENTIAL_MODELS = {
    'ssh_keys': SSHKey,
    'access_keys': AccessKey,
    'passkeys': Passkey,
    'private_token': PrivateToken,
}
COMMON_DETAIL_FIELDS = ('id', 'is_active', 'date_created', 'date_last_used')
DETAIL_FIELDS = {
    'ssh_keys': ('name',),
    'access_keys': (),
    'passkeys': ('name', 'platform'),
}


class UserCredentialPagination(LimitOffsetPagination):
    default_limit = 15
    max_limit = 100


def count_fields(source, label):
    return [
        serializers.IntegerField(source=f'{source}.{key}', label=format_lazy('{} ({})', label, title), read_only=True)
        for key, title in (('enabled', _('Enabled')), ('total', _('Total')))
    ]


class UserCredentialExportSerializer(serializers.Serializer):
    name = serializers.CharField(label=_('Name'), read_only=True)
    username = serializers.CharField(label=_('Username'), read_only=True)
    is_active = serializers.BooleanField(label=format_lazy('{} ({})', _('User'), _('Enabled')), read_only=True)
    ssh_enabled, ssh_total = count_fields('ssh_keys', _('SSH key'))
    access_enabled, access_total = count_fields('access_keys', _('Access key'))
    webauthn_enabled, webauthn_total = count_fields('passkeys', _('Passkey'))
    has_private_credential = serializers.BooleanField(source='private_token', label=_('Private token'), read_only=True)

    class Meta:
        model = User


class UserCredentialCSVRenderer(CSVFileRenderer):
    escape_chars = (*CSVFileRenderer.escape_chars, '+', '-')

    def render_value(self, field, value):
        # The shared CSV writer quotes leading zeroes in text identifiers. Keep counts numeric.
        if isinstance(field, serializers.IntegerField):
            return value
        return super().render_value(field, value)


class UserCredentialBaseApi(ListAPIView):
    permission_classes = (IsValidUser, RBACPermission)
    rbac_perms = {'*': 'rbac.view_usercredential'}
    perm_model = User
    pagination_class = UserCredentialPagination
    renderer_classes = (JSONRenderer,)
    metadata_class = SimpleMetadata
    http_method_names = ['get', 'head', 'options']
    filter_backends = ()

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Cache-Control'] = 'no-store'
        return response


class UserCredentialOverviewApi(UserCredentialBaseApi):
    search_fields = ('name', 'username')
    filter_backends = (SearchFilter, IDSpmFilterBackend)
    renderer_classes = (JSONRenderer, UserCredentialCSVRenderer, ExcelFileRenderer)
    serializer_class = UserCredentialExportSerializer
    export_non_filter_params = ('oid', 'limit', 'offset', 'template')

    def get_queryset(self):
        # Keep zero-credential and disabled users in the selected organization.
        return User.get_org_users().order_by('username', 'id').values(
            'id', 'name', 'username', 'is_active',
        )

    def filter_queryset(self, queryset):
        params = self.request.query_params
        if 'spm' in params and not is_uuid(params['spm']):
            return queryset.none()
        try:
            return super().filter_queryset(queryset)
        except (DjangoValidationError, TypeError, ValueError):
            # A cached selection from another list can contain non-user IDs.
            if 'spm' not in params and 'exclude_spm' not in params:
                raise
            return queryset.none()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        export = request.accepted_renderer.format in ('csv', 'xlsx')
        if export and request.query_params.get('template', 'export') != 'export':
            raise ValidationError({'detail': _('Invalid template')})
        users = list(queryset[:settings.MAX_LIMIT_PER_PAGE]) if export else self.paginate_queryset(queryset)
        user_ids = [user['id'] for user in users]
        for kind, model in CREDENTIAL_MODELS.items():
            credentials = model.objects.filter(user_id__in=user_ids).order_by()
            if kind == 'private_token':
                # Read existing one-to-one records; user.private_token would create one.
                holders = set(credentials.values_list('user_id', flat=True))
                for user in users:
                    user[kind] = user['id'] in holders
                continue
            counts = credentials.values('user_id').annotate(
                enabled=Count('pk', filter=Q(is_active=True)), total=Count('pk'),
            )
            by_user = {row['user_id']: row for row in counts}
            for user in users:
                count = by_user.get(user['id'], {})
                user[kind] = {'enabled': count.get('enabled', 0), 'total': count.get('total', 0)}

        if export:
            return Response(self.get_serializer(users, many=True).data)
        return self.get_paginated_response(users)


class UserCredentialDetailApi(UserCredentialBaseApi):
    def get_queryset(self):
        kind = self.kwargs['credential_type']
        model = CREDENTIAL_MODELS.get(kind)
        if model is None:
            raise NotFound()
        user = get_object_or_404(
            User.get_org_users().only('id'), pk=self.kwargs['user_id'],
        )
        # Fetch only metadata: never load/decrypt secret fields, even for serialization.
        credentials = model.objects.filter(user_id=user.id)
        if kind == 'private_token':
            # The primary key is the secret token: do not even select it.
            return credentials.order_by('-created').values(
                'date_last_used', date_created=F('created'),
            )
        return credentials.order_by('-date_created', 'id').values(
            *COMMON_DETAIL_FIELDS, *DETAIL_FIELDS[kind],
        )

    def list(self, request, *args, **kwargs):
        rows = self.paginate_queryset(self.get_queryset())
        for row in rows:
            if self.kwargs['credential_type'] == 'private_token':
                row['exists'] = True
                continue
            raw_id = str(row.pop('id'))
            # Keep stable, masked identifiers for the existing credential details.
            row['id'] = salted_hmac('audits.user_credentials', raw_id).hexdigest()
            row['identifier'] = f'{raw_id[:8]}…{raw_id[-4:]}'
        return self.get_paginated_response(rows)
