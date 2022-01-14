from django.db import models
from simple_history.models import HistoricalRecords
from django.utils.translation import ugettext_lazy as _

from common.utils import lazyproperty
from assets.models.base import BaseUser


class Account(BaseUser):
    app = models.ForeignKey('applications.Application', on_delete=models.CASCADE, null=True, verbose_name=_('Database'))
    systemuser = models.ForeignKey('assets.SystemUser', on_delete=models.CASCADE, null=True, verbose_name=_("System user"))
    version = models.IntegerField(default=1, verbose_name=_('Version'))
    history = HistoricalRecords()

    auth_attrs = ['username', 'password', 'private_key', 'public_key']

    class Meta:
        verbose_name = _('Account')
        unique_together = [('username', 'app', 'systemuser')]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_snapshot = {}

    def get_or_systemuser_attr(self, attr):
        val = getattr(self, attr, None)
        if val:
            return val
        if self.systemuser:
            return getattr(self.systemuser, attr, '')
        return ''

    def load_auth(self):
        for attr in self.auth_attrs:
            value = self.get_or_systemuser_attr(attr)
            self.auth_snapshot[attr] = [getattr(self, attr), value]
            setattr(self, attr, value)

    def unload_auth(self):
        if not self.systemuser:
            return

        for attr, values in self.auth_snapshot.items():
            origin_value, loaded_value = values
            current_value = getattr(self, attr, '')
            if current_value == loaded_value:
                setattr(self, attr, origin_value)

    def save(self, *args, **kwargs):
        self.unload_auth()
        instance = super().save(*args, **kwargs)
        self.load_auth()
        return instance

    @lazyproperty
    def category(self):
        return self.app.category

    @lazyproperty
    def type(self):
        return self.app.type

    @lazyproperty
    def attrs(self):
        return self.app.attrs

    @lazyproperty
    def app_display(self):
        return self.systemuser.name

    @property
    def username_display(self):
        return self.get_or_systemuser_attr('username') or ''

    @lazyproperty
    def systemuser_display(self):
        if not self.systemuser:
            return ''
        return str(self.systemuser)

    @property
    def smart_name(self):
        username = self.username_display

        if self.app:
            app = str(self.app)
        else:
            app = '*'
        return '{}@{}'.format(username, app)

    def __str__(self):
        return self.smart_name
