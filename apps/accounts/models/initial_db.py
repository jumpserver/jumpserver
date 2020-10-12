
from accounts.models import AccountType, PropField
from django.db import transaction

prop_field_data = [
    {'id': 1, 'name': 'port', 'type': PropField.PropType.INT, 'required': 1},
    {'id': 2, 'name': 'subnet', 'type': PropField.PropType.IP, 'required': 0},
    {'id': 3, 'name': 'gateway', 'type': PropField.PropType.IP, 'required': 0},
    {'id': 4, 'name': 'dns', 'type': PropField.PropType.IP, 'required': 0},
    {'id': 5, 'name': 'ssh-key', 'type': PropField.PropType.STR, 'required': 1},
    {'id': 6, 'name': 'db-name', 'type': PropField.PropType.STR, 'required': 1},
]

account_type_data = [
    {'name': 'app', 'category': AccountType.Category.APP, 'base_type': None, 'protocol': 'HTTPS', 'prop_fields': []},
    {'name': 'mysql', 'category': AccountType.Category.DATABASE, 'base_type': None, 'protocol': 'TCP/IP', 'prop_fields': [1,6]},
    {'name': 'unix_ssh', 'category': AccountType.Category.OS, 'base_type': None, 'protocol': 'SSH', 'prop_fields': [1]},
    {'name': 'unix_ssh_key', 'category': AccountType.Category.OS, 'base_type': None, 'protocol': 'SSH', 'prop_fields': [1,5]},
    {'name': 'network_device', 'category': AccountType.Category.NETWORK_DEVICE, 'base_type': None, 'protocol': 'SSH', 'prop_fields': [2,3,4]},
    {'name': 'windows_rdp', 'category': AccountType.Category.OS, 'base_type': None, 'protocol': 'RDP', 'prop_fields': [1]},
]


def initial_account_type(sender, **kwargs):

    with transaction.atomic():
        for data in prop_field_data:
            PropField.objects.get_or_create(data, id=data['id'])

        for data in account_type_data:
            data['created_by'] = 'init_db'
            prop_fields_ids = data.pop('prop_fields')
            obj, created = AccountType.objects.get_or_create(data, name=data['name'])
            if len(prop_fields_ids) > 0:
                obj.prop_fields.add(*prop_fields_ids)

