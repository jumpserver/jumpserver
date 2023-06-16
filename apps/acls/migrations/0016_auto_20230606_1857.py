# Generated by Django 3.2.17 on 2023-06-06 10:57
from collections import defaultdict

from django.db import migrations, models

import common.db.fields


def migrate_users_login_acls(apps, schema_editor):
    login_acl_model = apps.get_model('acls', 'LoginACL')
    name_used = defaultdict(int)

    login_acls = []
    for login_acl in login_acl_model.objects.all():
        name = login_acl.name.lower()
        if name_used[name] > 0:
            name += "_{}".format(name_used[name])
        name_used[name] += 1
        login_acl.name = name
        login_acl.users = {
            "type": "ids", "ids": [str(login_acl.user_id)]
        }
        login_acls.append(login_acl)

    login_acl_model.objects.bulk_update(login_acls, ['name', 'users'])


class Migration(migrations.Migration):
    dependencies = [
        ('acls', '0015_connectmethodacl'),
    ]

    operations = [
        migrations.AddField(
            model_name='loginacl',
            name='users',
            field=common.db.fields.JSONManyToManyField(default=dict, to='users.User', verbose_name='Users'),
        ),
        migrations.RunPython(migrate_users_login_acls),
        migrations.RemoveField(
            model_name='loginacl',
            name='user',
        ),
        migrations.AlterField(
            model_name='loginacl',
            name='name',
            field=models.CharField(max_length=128, unique=True, verbose_name='Name'),
        ),
    ]
