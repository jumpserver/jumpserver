# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

"""
该模块主要用于提供一个统一的api来管理sudo的配置文件,
支持管理的系统包括： ubuntu(/etc/sudoers)

因为sudoers配置文件很危险,所以采用生成临时文件, 验证ok后, 进行替换来变更
"""


from jinja2 import Template


__sudoers_tmp__ = """# management by JumpServer
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
{% if privileges -%}
{% for User_Flag, Host_Flag, Runas_Flag, Command_Flag, NopassWord in privileges -%}
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


class Sudo(object):
    """
    Sudo配置文件API, 用于配置sudo的配置文件

    :param user_alias: <dict> {<alia>: <users_list>}
    :param cmnd_alias: <dict> {<alia>: <commands_list>}
    :param host_alias: <dict> {<alia>: <hosts_list>}
    :param runas_alias: <dict> {<alia>: <runas_list>}
    :param extra_lines: <list> [<line1>, <line2>,...]
    :param privileges: <list> [(user, host, runas, command, nopassword),]
    """

    def __init__(self, user_alias, cmnd_alias, privileges, host_alias=None, runas_alias=None, extra_lines=None):
        self.extras = extra_lines
        self.users = user_alias
        self.commands = cmnd_alias
        self.hosts = host_alias
        self.runas = runas_alias
        self.privileges = privileges

    def get_tmp(self):
        template = Template(__sudoers_tmp__)
        context = {"User_Alias": self.users,
                   "Cmnd_Alias": self.commands,
                   "Host_Alias": self.hosts,
                   "Runas_Alias": self.runas,
                   "Extra_Lines": self.extras,
                   "privileges": self.privileges}
        return template.render(context)

    def gen_privileges(self):
        pass

    def get_sudo_from_db(self):
        pass

    def check_users(self):
        pass

    def check_commands(self):
        pass

    def check_hosts(self):
        pass

    def check_runas(self):
        pass

    def check_privileges(self):
        pass


if __name__ == "__main__":
    users = {"a": ['host1, host2'], "b": ["host3", "host4"]}
    commands = {"dba": ["bin/bash"], "dev": ["bin/bash"]}
    privileges = [("a", "ALL", "root", "dba", True), ("a", "ALL", "root", "dba", False)]
    sudo = Sudo(users, commands, privileges, extra_lines=['aaaaaasf sdfasdf', 'bbbbb sfdsdf'])
    print sudo.get_tmp()

