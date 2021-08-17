from django.db import migrations
from django.db.transaction import atomic

default_id = '00000000-0000-0000-0000-000000000002'


def change_key0_to_key1(apps, schema_editor):
    from orgs.utils import set_current_org

    # https://stackoverflow.com/questions/28777338/django-migrations-runpython-not-able-to-call-model-methods
    Organization = apps.get_model('orgs', 'Organization')
    Node = apps.get_model('assets', 'Node')

    print()
    org = Organization.objects.get(id=default_id)
    set_current_org(org)

    exists_0 = Node.objects.filter(key__startswith='0').exists()
    if not exists_0:
        print(f'--> Not exist key=0 nodes, do nothing.')
        return

    key_1_count = Node.objects.filter(key__startswith='1').count()
    if key_1_count > 1:
        print(f'--> Node key=1 have children, can`t just delete it. Please contact JumpServer team')
        return

    root_node = Node.objects.filter(key='1').first()
    if root_node and root_node.assets.exists():
        print(f'--> Node key=1 has assets, do nothing.')
        return

    with atomic():
        if root_node:
            print(f'--> Delete node key=1')
            root_node.delete()

        nodes_0 = Node.objects.filter(key__startswith='0')

        for n in nodes_0:
            old_key = n.key
            key_list = n.key.split(':')
            key_list[0] = '1'
            new_key = ':'.join(key_list)
            new_parent_key = ':'.join(key_list[:-1])
            n.key = new_key
            n.parent_key = new_parent_key
            n.save()
            print('--> Modify key ( {} > {} )'.format(old_key, new_key))


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0010_auto_20210219_1241'),
        ('assets', '0068_auto_20210312_1455'),
    ]

    operations = [
        migrations.RunPython(change_key0_to_key1)
    ]
