from django.db import models

from common.db.models import JMSModel

__all__ = ('SystemMsgSubscription', 'UserMsgSubscription')


class UserMsgSubscription(JMSModel):
    message_type = models.CharField(max_length=128)
    user = models.ForeignKey('users.User', related_name='user_msg_subscriptions', on_delete=models.CASCADE)
    receive_backends = models.JSONField(default=list)

    def __str__(self):
        return f'{self.message_type}'


class SystemMsgSubscription(JMSModel):
    message_type = models.CharField(max_length=128, unique=True)
    users = models.ManyToManyField('users.User', related_name='system_msg_subscriptions')
    groups = models.ManyToManyField('users.UserGroup', related_name='system_msg_subscriptions')
    receive_backends = models.JSONField(default=list)

    message_type_label = ''

    def __str__(self):
        return f'{self.message_type}'

    def __repr__(self):
        return self.__str__()

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
