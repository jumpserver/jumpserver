from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.mixins.models import CommonModelMixin

__all__ = ['LoginConfirmOrder', 'Comment']


class Comment(CommonModelMixin):
    order_id = models.UUIDField()
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, verbose_name=_("User"), related_name='comments')
    user_display = models.CharField(max_length=128, verbose_name=_("User display name"))
    body = models.TextField(verbose_name=_("Body"))

    class Meta:
        ordering = ('date_created', )


class BaseOrder(CommonModelMixin):
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_PENDING = 'pending'
    STATUS_CHOICES = (
        (STATUS_ACCEPTED, _("Accepted")),
        (STATUS_REJECTED, _("Rejected")),
        (STATUS_PENDING, _("Pending"))
    )
    TYPE_LOGIN_CONFIRM = 'login_confirm'
    TYPE_CHOICES = (
        (TYPE_LOGIN_CONFIRM, 'Login confirm'),
    )
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='%(class)s_requested', verbose_name=_("User"))
    user_display = models.CharField(max_length=128, verbose_name=_("User display name"))

    title = models.CharField(max_length=256, verbose_name=_("Title"))
    body = models.TextField(verbose_name=_("Body"))
    assignee = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='%(class)s_handled', verbose_name=_("Assignee"))
    assignee_display = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Assignee display name"))
    assignees = models.ManyToManyField('users.User', related_name='%(class)s_assigned', verbose_name=_("Assignees"))
    assignees_display = models.CharField(max_length=128, verbose_name=_("Assignees display name"), blank=True)
    type = models.CharField(choices=TYPE_CHOICES, max_length=16, verbose_name=_('Type'))
    status = models.CharField(choices=STATUS_CHOICES, max_length=16, default='pending')

    def __str__(self):
        return '{}: {}'.format(self.user_display, self.title)

    @property
    def comments(self):
        return Comment.objects.filter(order_id=self.id)

    @property
    def body_as_html(self):
        return self.body.replace('\n', '<br/>')

    @property
    def status_display(self):
        return self.get_status_display()

    class Meta:
        abstract = True
        ordering = ('-date_created',)


class LoginConfirmOrder(BaseOrder):
    ip = models.GenericIPAddressField(blank=True, null=True)
    city = models.CharField(max_length=16, blank=True, default='')
