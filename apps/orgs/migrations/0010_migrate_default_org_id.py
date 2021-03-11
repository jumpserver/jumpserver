from django.db import migrations


default_id = '00000000-0000-0000-0000-000000000001'


def add_default_org(apps, schema_editor):
    org_cls = apps.get_model('orgs', 'Organization')
    defaults = {'name': 'DEFAULT', 'id': default_id}
    org_cls.objects.get_or_create(defaults=defaults, id=default_id)


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0009_auto_20201023_1628'),
    ]

    operations = [
        migrations.RunPython(add_default_org),
    ]
