from common.api import JMSModelViewSet
from common.permissions import IsValidUser
from ..serializers import SSHKeySerializer
from users.notifications import ResetPublicKeySuccessMsg


class SSHkeyViewSet(JMSModelViewSet):
    serializer_class = SSHKeySerializer
    permission_classes = [IsValidUser]
    filterset_fields = ('name', 'is_active')
    search_fields = ('name',)
    ordering = ('-date_last_used', '-date_created')

    def get_queryset(self):
        return self.request.user.ssh_keys.all()

    def perform_update(self, serializer):
        super().perform_update(serializer)
        ResetPublicKeySuccessMsg(self.request.user, self.request).publish_async()
