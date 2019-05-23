#  coding: utf-8
#

from django.utils.translation import ugettext_lazy as _


# RemoteApp
REMOTE_APP_BOOT_PROGRAM_NAME = '||jmservisor'

REMOTE_APP_TYPE_CHROME = 'chrome'
REMOTE_APP_TYPE_MYSQL_WORKBENCH = 'mysql_workbench'
REMOTE_APP_TYPE_VMWARE_CLIENT = 'vmware_client'
REMOTE_APP_TYPE_CUSTOM = 'custom'

REMOTE_APP_TYPE_CHOICES = (
    (
        _('Browser'),
        (
            (REMOTE_APP_TYPE_CHROME, 'Chrome'),
        )
    ),
    (
        _('Database tools'),
        (
            (REMOTE_APP_TYPE_MYSQL_WORKBENCH, 'MySQL Workbench'),
        )
    ),
    (
        _('Virtualization tools'),
        (
            (REMOTE_APP_TYPE_VMWARE_CLIENT, 'vSphere Client'),
        )
    ),
    (REMOTE_APP_TYPE_CUSTOM, _('Custom')),

)

# Fields attribute write_only default => False

REMOTE_APP_TYPE_CHROME_FIELDS = [
    {'name': 'chrome_target'},
    {'name': 'chrome_username'},
    {'name': 'chrome_password', 'write_only': True}
]
REMOTE_APP_TYPE_MYSQL_WORKBENCH_FIELDS = [
    {'name': 'mysql_workbench_ip'},
    {'name': 'mysql_workbench_name'},
    {'name': 'mysql_workbench_username'},
    {'name': 'mysql_workbench_password', 'write_only': True}
]
REMOTE_APP_TYPE_VMWARE_CLIENT_FIELDS = [
    {'name': 'vmware_target'},
    {'name': 'vmware_username'},
    {'name': 'vmware_password', 'write_only': True}
]
REMOTE_APP_TYPE_CUSTOM_FIELDS = [
    {'name': 'custom_cmdline'},
    {'name': 'custom_target'},
    {'name': 'custom_username'},
    {'name': 'custom_password', 'write_only': True}
]

REMOTE_APP_TYPE_MAP_FIELDS = {
    REMOTE_APP_TYPE_CHROME: REMOTE_APP_TYPE_CHROME_FIELDS,
    REMOTE_APP_TYPE_MYSQL_WORKBENCH: REMOTE_APP_TYPE_MYSQL_WORKBENCH_FIELDS,
    REMOTE_APP_TYPE_VMWARE_CLIENT: REMOTE_APP_TYPE_VMWARE_CLIENT_FIELDS,
    REMOTE_APP_TYPE_CUSTOM: REMOTE_APP_TYPE_CUSTOM_FIELDS
}
