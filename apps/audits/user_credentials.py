from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404
from django.utils.crypto import salted_hmac
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView
from rest_framework.metadata import SimpleMetadata
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.renderers import JSONRenderer

from authentication.backends.passkey.models import Passkey
from authentication.models import AccessKey, PrivateToken, SSHKey
from common.drf.filters import SearchFilter
from common.permissions import IsValidUser
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
    filter_backends = (SearchFilter,)

    def get_queryset(self):
        # Keep zero-credential and disabled users in the selected organization.
        return User.get_org_users().order_by('username', 'id').values(
            'id', 'name', 'username', 'is_active',
        )

    def list(self, request, *args, **kwargs):
        users = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        user_ids = [user['id'] for user in users]
        for kind, model in CREDENTIAL_MODELS.items():
            # One query per type, bounded to users on this page in the selected org.
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
