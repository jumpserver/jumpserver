from common.drf.filters import BaseFilterSet
from users.models.user import User


class UserFilter(BaseFilterSet):
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'name', 'source'
        )


