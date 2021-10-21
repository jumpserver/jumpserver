from django_filters import rest_framework as filters
from common.drf.filters import BaseFilterSet

from acls.models import LoginACL


class LoginAclFilter(BaseFilterSet):
    user = filters.UUIDFilter(field_name='user_id')
    user_display = filters.CharFilter(field_name='user__name')

    class Meta:
        model = LoginACL
        fields = (
            'name', 'user', 'user_display', 'action'
        )
