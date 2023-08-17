from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel, CASCADE_SIGNAL_SKIP

__all__ = ('SystemMsgSubscription', 'UserMsgSubscription')


class UserMsgSubscription(JMSBaseModel):
    user = models.OneToOneField(
        'users.User', related_name='user_msg_subscription', on_delete=CASCADE_SIGNAL_SKIP,
        verbose_name=_('User')
    )
    receive_backends = models.JSONField(default=list, verbose_name=_('receive backend'))
    comment = ''

    class Meta:
        verbose_name = _('User message')

    def __str__(self):
        return _('{} subscription').format(self.user)


class SystemMsgSubscription(JMSBaseModel):
    message_type = models.CharField(max_length=128, unique=True)
    users = models.ManyToManyField('users.User', related_name='system_msg_subscriptions')
    groups = models.ManyToManyField('users.UserGroup', related_name='system_msg_subscriptions')
    receive_backends = models.JSONField(default=list)
    comment = ''

    message_type_label = ''

    class Meta:
        verbose_name = _('System message')

    def set_message_type_label(self):
        # 采用手动调用，没设置成 property 的方式
        # 因为目前只有界面修改时会用到这个属性，避免实例化时占用资源计算
        from ..notifications import system_msgs
        msg_label = ''
        for msg in system_msgs:
            if msg.get('message_type') == self.message_type:
                msg_label = msg.get('message_type_label', '')
                break
        self.message_type_label = msg_label

    @property
    def receivers(self):
        from notifications.backends import BACKEND

        users = [user for user in self.users.all()]

        for group in self.groups.all():
            for user in group.users.all():
                users.append(user)

        receive_backends = self.receive_backends
        receviers = []

        for user in users:
            recevier = {'name': str(user), 'id': user.id}
            for backend in receive_backends:
                recevier[backend] = bool(BACKEND(backend).get_account(user))
            receviers.append(recevier)

        return receviers

    def __str__(self):
        return f'{self.message_type_label}' or f'{self.message_type}'

    def __repr__(self):
        return self.__str__()
