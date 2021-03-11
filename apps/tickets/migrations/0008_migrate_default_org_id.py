import time
import sys

from django.db import migrations


default_id = '00000000-0000-0000-0000-000000000001'


def migrate_default_org_id(apps, schema_editor):
    org_app_models = [
        ('tickets', ['Ticket']),
    ]
    print("")
    for app, models_name in org_app_models:
        for model_name in models_name:
            t_start = time.time()
            print("Migrate model org id: {}".format(model_name), end='')
            sys.stdout.flush()

            model_cls = apps.get_model(app, model_name)
            model_cls.objects.filter(org_id='').update(org_id=default_id)
            interval = round((time.time() - t_start) * 1000, 2)
            print(" done, use {} ms".format(interval))


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0007_auto_20201224_1821'),
        ('orgs', '0010_migrate_default_org_id'),
    ]

    operations = [
        migrations.RunPython(migrate_default_org_id),
    ]
