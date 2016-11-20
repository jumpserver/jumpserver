# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals, absolute_import

import logging
import json

from jinja2 import Template
from django.db import models
from assets.models import Asset
from django.utils.translation import ugettext_lazy as _


logger = logging.getLogger(__name__)


class Tasker(models.Model):
    uuid = models.CharField(max_length=128, verbose_name=_('UUID'), primary_key=True)
    name = models.CharField(max_length=128, blank=True, verbose_name=_('Name'))
    start = models.DateTimeField(auto_now_add=True, verbose_name=_('Start Time'))
    end = models.DateTimeField(blank=True, null=True, verbose_name=_('End Time'))
    exit_code = models.IntegerField(default=0, verbose_name=_('Exit Code'))
    completed = models.BooleanField(default=False, verbose_name=_('Is Completed'))
    hosts = models.TextField(blank=True, null=True, verbose_name=_('Hosts'))

    def __unicode__(self):
        return "%s" % self.uuid

    @property
    def total_hosts(self):
        return self.hosts.split(',')


class AnsiblePlay(models.Model):
    tasker = models.ForeignKey(Tasker, related_name='plays', blank=True, null=True)
    uuid = models.CharField(max_length=128, verbose_name=_('UUID'), primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_('Name'))

    def __unicode__(self):
        return "%s<%s>" % (self.name, self.uuid)

    def to_dict(self):
        return {"uuid": self.uuid, "name": self.name}


class AnsibleTask(models.Model):
    play = models.ForeignKey(AnsiblePlay, related_name='tasks', blank=True, null=True)
    uuid = models.CharField(max_length=128, verbose_name=_('UUID'), primary_key=True)
    name = models.CharField(max_length=128, blank=True, verbose_name=_('Name'))

    def __unicode__(self):
        return "%s<%s>" % (self.name, self.uuid)

    def to_dict(self):
        return {"uuid": self.uuid, "name": self.name}

    def failed(self):
        pass

    def success(self):
        pass


class AnsibleHostResult(models.Model):
    task = models.ForeignKey(AnsibleTask, related_name='host_results', blank=True, null=True)
    name = models.CharField(max_length=128, blank=True, verbose_name=_('Name'))
    success = models.TextField(blank=True, verbose_name=_('Success'))
    skipped = models.TextField(blank=True, verbose_name=_('Skipped'))
    failed = models.TextField(blank=True, verbose_name=_('Failed'))
    unreachable = models.TextField(blank=True, verbose_name=_('Unreachable'))
    no_host = models.TextField(blank=True, verbose_name=_('NoHost'))

    def __unicode__(self):
        return "%s %s<%s>" % (self.name, str(self.is_success), self.task.uuid)

    @property
    def is_failed(self):
        if self.failed or self.unreachable or self.no_host:
            return True
        return False

    @property
    def is_success(self):
        return not self.is_failed

    @property
    def _success_data(self):
        if self.success:
            return json.loads(self.success)
        elif self.skipped:
            return json.loads(self.skipped)

    @property
    def _failed_data(self):
        if self.failed:
            return json.loads(self.failed)
        elif self.unreachable:
            return json.loads(self.unreachable)
        elif self.no_host:
            return {"msg": self.no_host}

    @property
    def failed_msg(self):
        return self._failed_data.get("msg")

    @staticmethod
    def __filter_disk(ansible_devices, exclude_devices):
        """
        过滤磁盘设备，丢弃掉不需要的设备

        :param ansible_devices: 对应的facts字段
        :param exclude_devices: <list> 一个需要被丢弃的设备,匹配规则是startwith, 比如需要丢弃sr0子类的 ['sr']
        :return: <dict> 过滤获取的结果
        """
        for start_str in exclude_devices:
            for key in ansible_devices.keys():
                if key.startswith(start_str):
                    ansible_devices.pop(key)
        return ansible_devices

    @staticmethod
    def __filter_interface(ansible_interfaces, exclude_interface):
        """
        过滤网卡设备，丢弃掉不需要的网卡， 比如lo

        :param ansible_interface: 对应的facts字段
        :param exclude_interface: <list> 一个需要被丢弃的设备,匹配规则是startwith, 比如需要丢弃lo子类的 ['lo']
        :return: <dict> 过滤获取的结果
        """
        for interface in ansible_interfaces:
            for start_str in exclude_interface:
                if interface.startswith(start_str):
                    i = ansible_interfaces.index(interface)
                    ansible_interfaces.pop(i)
        return ansible_interfaces

    @staticmethod
    def __gather_interface(facts, interfaces):
        """
        收集所有interface的具体信息

        :param facts: ansible faces
        :param interfaces: 需要收集的intreface列表
        :return: <dict> interface的详情
        """
        result = {}
        for key in interfaces:
            gather_key = "ansible_" + key
            if gather_key in facts.keys():
                result[key] = facts.get(gather_key)
        return result

    def __deal_setup(self):
        """
        处理ansible setup模块收集到的数据，提取资产需要的部分

        :return: <dict> {"msg": <str>, "data": <dict>}, 注意msg是异常信息, 有msg时 data为None
        """
        result = self._success_data
        module_name = result['invocation'].get('module_name') if result.get('invocation') else None
        if module_name is not None:
            if module_name != "setup":
                return {"msg": "the property only for ansible setup module result!, can't support other module", "data":None}
            else:
                data = {}
                facts =result.get('ansible_facts')
                interfaces = self.__filter_interface(facts.get('ansible_interfaces'), ['lo'])

                cpu_describe = "%s %s" % (facts.get('ansible_processor')[0], facts.get('ansible_processor')[1]) if len(facts.get('ansible_processor')) >= 2 else ""

                data['sn'] = facts.get('ansible_product_serial')
                data['env'] = facts.get('ansible_env')
                data['os'] = "%s %s(%s)" % (facts.get('ansible_distribution'),
                                         facts.get('ansible_distribution_version'),
                                         facts.get('ansible_distribution_release'))
                data['mem'] = facts.get('ansible_memtotal_mb')
                data['cpu'] = "%s %d核" % (cpu_describe, facts.get('ansible_processor_count'))
                data['disk'] = self.__filter_disk(facts.get('ansible_devices'), ['sr'])
                data['interface'] = self.__gather_interface(facts, interfaces)
                return {"msg": None, "data": data}
        else:
            return {"msg": "there result isn't ansible setup module result! can't process this data format", "data": None}

    @property
    def deal_setup(self):
        try:
            return self.__deal_setup()
        except Exception as e:
            return {"msg": "deal with setup data failed, %s" % e.message, "data": None}

    def __deal_ping(self):
        """
        处理ansible ping模块收集到的数据

        :return: <dict> {"msg": <str>, "data": {"success": <bool>}}, 注意msg是异常信息, 有msg时 data为None
        """
        result = self._success_data
        module_name = result['invocation'].get('module_name') if result.get('invocation') else None
        if module_name is not None:
            if module_name != "ping":
                return {"msg": "the property only for ansible setup module result!, can't support other module", "data":None}
            else:
                ping = True if result.get('ping') == "pong" else False

                return {"msg": None, "data": {"success": ping}}
        else:
            return {"msg": "there isn't module_name field! can't process this data format", "data": None}

    @property
    def deal_ping(self):
        try:
            return self.__deal_ping()
        except Exception as e:
            return {"msg": "deal with ping data failed, %s" % e.message, "data": None}


class HostAlia(models.Model):
    name = models.CharField(max_length=128, blank=True, null=True, unique=True, verbose_name=_('Host_Alias'))
    host_items = models.TextField(blank=True, null=True, verbose_name=_('Host_Items'))

    def __unicode__(self):
        return self.name


class UserAlia(models.Model):
    name = models.CharField(max_length=128, blank=True, null=True, unique=True, verbose_name=_('User_Alias'))
    user_items = models.TextField(blank=True, null=True, verbose_name=_('Host_Items'))

    def __unicode__(self):
        return self.name


class CmdAlia(models.Model):
    name = models.CharField(max_length=128, blank=True, null=True, unique=True, verbose_name=_('Command_Alias'))
    cmd_items = models.TextField(blank=True, null=True, verbose_name=_('Host_Items'))

    def __unicode__(self):
        return self.name


class RunasAlia(models.Model):
    name = models.CharField(max_length=128, blank=True, null=True, unique=True, verbose_name=_('Runas_Alias'))
    runas_items = models.TextField(blank=True, null=True, verbose_name=_('Host_Items'))

    def __unicode__(self):
        return self.name


class Privilege(models.Model):
    user = models.ForeignKey(UserAlia, blank=True, null=True, related_name='privileges')
    host = models.ForeignKey(HostAlia, blank=True, null=True, related_name='privileges')
    runas = models.ForeignKey(RunasAlia, blank=True, null=True, related_name='privileges')
    command = models.ForeignKey(CmdAlia, blank=True, null=True, related_name='privileges')
    nopassword = models.BooleanField(default=True, verbose_name=_('Is_NoPassword'))

    def __unicode__(self):
        return "[%s %s %s %s %s]" % (self.user.name,
                                     self.host.name,
                                     self.runas.name,
                                     self.command.name,
                                     self.nopassword)

    def to_tuple(self):
        return self.user.name, self.host.name, self.runas.name, self.command.name, self.nopassword


class Extra_conf(models.Model):
    line = models.TextField(blank=True, null=True, verbose_name=_('Extra_Item'))

    def __unicode__(self):
        return self.line


class Sudo(models.Model):
    """
    Sudo配置文件对象, 用于配置sudo的配置文件

    :param extra_lines: <list> [<line1>, <line2>,...]
    :param privileges: <list> [(user, host, runas, command, nopassword),]
    """

    asset = models.ForeignKey(Asset, null=True, blank=True, related_name='sudos')
    extra_lines = models.ManyToManyField(Extra_conf, related_name='sudos', blank=True)
    privilege_items = models.ManyToManyField(Privilege, related_name='sudos', blank=True)

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











