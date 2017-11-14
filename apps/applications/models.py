from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from users.models import User


class Terminal(models.Model):
    name = models.CharField(max_length=32, unique=True, verbose_name=_('Name'))
    remote_addr = models.CharField(max_length=128, verbose_name=_('Remote Address'))
    ssh_port = models.IntegerField(verbose_name=_('SSH Port'), default=2222)
    http_port = models.IntegerField(verbose_name=_('HTTP Port'), default=5000)
    user = models.OneToOneField(User, related_name='terminal', verbose_name='Application User', null=True, on_delete=models.CASCADE)
    is_accepted = models.BooleanField(default=False, verbose_name='Is Accepted')
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True, verbose_name=_('Comment'))

    @property
    def is_active(self):
        if self.user and self.user.is_active:
            return True
        return False

    @is_active.setter
    def is_active(self, active):
        if self.user:
            self.user.is_active = active
            self.user.save()

    def create_app_user(self):
        user, access_key = User.create_app_user(name=self.name, comment=self.comment)
        self.user = user
        self.save()
        return user, access_key

    def delete(self, using=None, keep_parents=False):
        if self.user:
            self.user.delete()
        self.is_deleted = True
        self.save()
        return

    def __str__(self):
        status = "Active"
        if not self.is_accepted:
            status = "NotAccept"
        elif self.is_deleted:
            status = "Deleted"
        elif not self.is_active:
            status = "Disable"
        return '%s: %s' % (self.name, status)

    class Meta:
        ordering = ('is_accepted',)


class TerminalStatus(models.Model):
    session_online = models.IntegerField(verbose_name=_("Session Online"), default=0)
    cpu_used = models.FloatField(verbose_name=_("CPU Usage"))
    memory_used = models.FloatField(verbose_name=_("Memory Used"))
    connections = models.IntegerField(verbose_name=_("Connections"))
    threads = models.IntegerField(verbose_name=_("Threads"))
    boot_time = models.FloatField(verbose_name=_("Boot Time"))
    terminal = models.ForeignKey(Terminal, null=True, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'terminal_status'

    # def __str__(self):
    #     return "<{} status>".format(self.terminal.name)


class TerminalSession(models.Model):
    LOGIN_FROM_CHOICES = (
        ('ST', 'SSH Terminal'),
        ('WT', 'Web Terminal'),
    )

    id = models.UUIDField(primary_key=True)
    user = models.CharField(max_length=128, verbose_name=_("User"))
    asset = models.CharField(max_length=1024, verbose_name=_("Asset"))
    system_user = models.CharField(max_length=128, verbose_name=_("System User"))
    login_from = models.CharField(max_length=2, choices=LOGIN_FROM_CHOICES, default="ST")
    is_finished = models.BooleanField(default=False)
    terminal = models.IntegerField(null=True, verbose_name=_("Terminal"))
    date_start = models.DateTimeField(verbose_name=_("Date Start"))
    date_end = models.DateTimeField(verbose_name=_("Date End"), null=True)

    class Meta:
        db_table = "terminal_session"

    def __str__(self):
        return "{0.id} of {0.user} to {0.asset}".format(self)


class TerminalTask(models.Model):
    name = models.CharField(max_length=128, verbose_name=_("Name"))
    args = models.CharField(max_length=1024, verbose_name=_("Task Args"))
    terminal = models.ForeignKey(Terminal, null=True, on_delete=models.CASCADE)
    is_finished = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_finished = models.DateTimeField(null=True)

    class Meta:
        db_table = "terminal_task"
