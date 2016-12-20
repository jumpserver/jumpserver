# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals, absolute_import

import logging

from jinja2 import Template
from django.db import models
from django.utils.timezone import now
from assets.models import Asset, AssetGroup
from django.utils.translation import ugettext_lazy as _

logger = logging.getLogger(__name__)

__all__ = ["HostAlia", "UserAlia", "CmdAlia", "RunasAlia", "Privilege", "Extra_conf", "Sudo"]


class HostAlia(models.Model):
    name = models.CharField(max_length=128, blank=True, null=True, unique=True, verbose_name=_('Host_Alias'))
    host_items = models.TextField(blank=True, null=True, verbose_name=_('Host_Items'))

    def __unicode__(self):
        return self.name

    @classmethod
    def generate_fake(cls, count=20):
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            hostA = cls(name=forgery_py.name.full_name(),
                       host_items=forgery_py.lorem_ipsum.sentence(),
                        )
            try:
                hostA.save()
                logger.debug('Generate fake host alia: %s' % hostA.name)
            except Exception as e:
                print('Error: %s, continue...' % e.message)
                continue


class UserAlia(models.Model):
    name = models.CharField(max_length=128, blank=True, null=True, unique=True, verbose_name=_('User_Alias'))
    user_items = models.TextField(blank=True, null=True, verbose_name=_('Host_Items'))

    def __unicode__(self):
        return self.name

    @classmethod
    def generate_fake(cls, count=20):
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            userA = cls(name=forgery_py.name.full_name(),
                        user_items=forgery_py.lorem_ipsum.sentence(),
                       )
            try:
                userA.save()
                logger.debug('Generate fake host alia: %s' % userA.name)
            except Exception as e:
                print('Error: %s, continue...' % e.message)
                continue


class CmdAlia(models.Model):
    name = models.CharField(max_length=128, blank=True, null=True, unique=True, verbose_name=_('Command_Alias'))
    cmd_items = models.TextField(blank=True, null=True, verbose_name=_('Host_Items'))

    def __unicode__(self):
        return self.name

    @classmethod
    def generate_fake(cls, count=20):
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            cmdA = cls(name=forgery_py.name.full_name(),
                       cmd_items=forgery_py.lorem_ipsum.sentence(),
                       )
            try:
                cmdA.save()
                logger.debug('Generate fake command alia: %s' % cmdA.name)
            except Exception as e:
                print('Error: %s, continue...' % e.message)
                continue


class RunasAlia(models.Model):
    name = models.CharField(max_length=128, blank=True, null=True, unique=True, verbose_name=_('Runas_Alias'))
    runas_items = models.TextField(blank=True, null=True, verbose_name=_('Host_Items'))

    def __unicode__(self):
        return self.name

    @classmethod
    def generate_fake(cls, count=20):
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            runas = cls(name=forgery_py.name.full_name(),
                       runas_items=forgery_py.lorem_ipsum.sentence(),
                       )
            try:
                runas.save()
                logger.debug('Generate fake RunAs alia: %s' % runas.name)
            except Exception as e:
                print('Error: %s, continue...' % e.message)
                continue


class Privilege(models.Model):
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    user = models.ForeignKey(UserAlia, blank=True, null=True, related_name='privileges')
    host = models.ForeignKey(HostAlia, blank=True, null=True, related_name='privileges')
    runas = models.ForeignKey(RunasAlia, blank=True, null=True, related_name='privileges')
    command = models.ForeignKey(CmdAlia, blank=True, null=True, related_name='privileges')
    nopassword = models.BooleanField(default=True, verbose_name=_('Is_NoPassword'))
    comment = models.TextField(blank=True, null=True, verbose_name=_('Comment'))

    def __unicode__(self):
        return "[%s %s %s %s %s]" % (self.user.name,
                                     self.host.name,
                                     self.runas.name,
                                     self.command.name,
                                     self.nopassword)

    def to_tuple(self):
        return self.user.name, self.host.name, self.runas.name, self.command.name, self.nopassword

    @classmethod
    def generate_fake(cls, count=20):
        from random import seed, choice
        import forgery_py

        seed()
        for i in range(count):
            pri = cls(name=forgery_py.name.full_name(),
                       comment=forgery_py.lorem_ipsum.sentence(),
                      )
            try:
                pri.user = choice(UserAlia.objects.all())
                pri.host = choice(HostAlia.objects.all())
                pri.runas = choice(RunasAlia.objects.all())
                pri.command = choice(CmdAlia.objects.all())
                pri.save()
                logger.debug('Generate fake privileges: %s' % pri.name)
            except Exception as e:
                print('Error: %s, continue...' % e.message)
                continue


class Extra_conf(models.Model):
    line = models.TextField(blank=True, null=True, verbose_name=_('Extra_Item'),
                            help_text=_('The extra sudo config line.'))

    def __unicode__(self):
        return self.line


class Sudo(models.Model):
    """
    Sudo配置文件对象, 用于配置sudo的配置文件

    :param extra_lines: <list> [<line1>, <line2>,...]
    :param privileges: <list> [(user, host, runas, command, nopassword),]
    """

    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'),
                            help_text=_('Name for this sudo'))
    created_time = models.DateTimeField(verbose_name=_('Created Time'), auto_created=True,
                                        help_text=_('The create time of this sudo'))
    modify_time = models.DateTimeField(auto_now=True, verbose_name=_('Modify Time'),
                                       help_text=_('The recent modify time of this sudo'))
    assets = models.ManyToManyField(Asset, blank=True, related_name='sudos')
    asset_groups = models.ManyToManyField(AssetGroup, blank=True, related_name='sudos')
    extra_lines = models.ManyToManyField(Extra_conf, related_name='sudos', blank=True)
    privilege_items = models.ManyToManyField(Privilege, related_name='sudos', blank=True)

    @property
    def all_assets(self):
        assets = list(self.assets.all())
        for group in self.asset_groups.all():
            for asset in group.assets.all():
                if asset not in assets:
                    assets.append(asset)
        return assets

    @property
    def users(self):
        return {privilege.user.name: privilege.user.user_items.split(',') for privilege in self.privilege_items.all()}

    @property
    def commands(self):
        return {privilege.command.name: privilege.command.cmd_items.split(',') for privilege in self.privilege_items.all()}

    @property
    def hosts(self):
        return {privilege.host.name: privilege.host.host_items.split(',') for privilege in self.privilege_items.all()}

    @property
    def runas(self):
        return {privilege.runas.name: privilege.runas.runas_items.split(',') for privilege in self.privilege_items.all()}

    @property
    def extras(self):
        return [extra.line for extra in self.extra_lines.all()]

    @property
    def privileges(self):
        return [privilege.to_tuple() for privilege in self.privilege_items.all()]

    @property
    def content(self):
        template = Template(self.__sudoers_jinja2_tmp__)
        context = {"User_Alias": self.users,
                   "Cmnd_Alias": self.commands,
                   "Host_Alias": self.hosts,
                   "Runas_Alias": self.runas,
                   "Extra_Lines": self.extras,
                   "Privileges": self.privileges}
        return template.render(context)

    @property
    def __sudoers_jinja2_tmp__(self):
        return """# management by JumpServer
# This file MUST be edited with the 'visudo' command as root.
#
# Please consider adding local content in /etc/sudoers.d/ instead of
# directly modifying this file.
#
# See the man page for details on how to write a sudoers file.
#
Defaults        env_reset
Defaults        secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# JumpServer Generate Other Configure is here
{% if Extra_Lines -%}
{% for line in Extra_Lines -%}
{{ line }}
{% endfor %}
{%- endif %}

# Host alias specification
{% if Host_Alias -%}
{% for flag, items in Host_Alias.iteritems() -%}
Host_Alias    {{ flag }} = {{ items|join(', ') }}
{% endfor %}
{%- endif %}

# User alias specification
{% if User_Alias -%}
{% for flag, items in User_Alias.iteritems() -%}
User_Alias    {{ flag }} = {{ items|join(', ') }}
{% endfor %}
{%- endif %}


# Cmnd alias specification
{% if Cmnd_Alias -%}
{% for flag, items in Cmnd_Alias.iteritems() -%}
Cmnd_Alias    {{ flag }} = {{ items|join(', ') }}
{% endfor %}
{%- endif %}

# Run as alias specification
{% if Runas_Alias -%}
{% for flag, items in Runas_Alias.iteritems() -%}
Runas_Alias    {{ flag }} = {{ items|join(', ') }}
{% endfor %}
{%- endif %}

# User privilege specification
root    ALL=(ALL:ALL) ALL

# JumpServer Generate User privilege is here.
# Note privileges is a tuple list like [(user, host, runas, command, nopassword),]
{% if Privileges -%}
{% for User_Flag, Host_Flag, Runas_Flag, Command_Flag, NopassWord in Privileges -%}
{% if NopassWord -%}
{{ User_Flag }} {{ Host_Flag }}=({{ Runas_Flag }}) NOPASSWD: {{ Command_Flag }}
{%- else -%}
{{ User_Flag }} {{ Host_Flag }}=({{ Runas_Flag }}) {{ Command_Flag }}
{%- endif %}
{% endfor %}
{%- endif %}

# Members of the admin group may gain root privileges
%admin ALL=(ALL) ALL

# Allow members of group sudo to execute any command
%sudo   ALL=(ALL:ALL) ALL

# See sudoers(5) for more information on "#include" directives:

#includedir /etc/sudoers.d
"""

    @classmethod
    def generate_fake(cls, count=20):
        from random import seed, choice
        import forgery_py

        seed()
        for i in range(count):
            sudo = cls(name=forgery_py.name.full_name(),
                       created_time=now()
                      )
            try:
                sudo.save()
                sudo.privilege_items = [choice(Privilege.objects.all())]
                sudo.save()
                logger.debug('Generate fake cron: %s' % sudo.name)
            except Exception as e:
                print('Error: %s, continue...' % e.message)
                continue