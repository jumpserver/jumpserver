# Generated by Django 4.1.13 on 2025-05-15 02:38

import common.utils.django
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('perms', '0002_auto_20171228_0025'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assetpermission',
            name='date_expired',
            field=models.DateTimeField(db_index=True, default=common.utils.django.asset_permission_date_expired_default, verbose_name='Date expired'),
        ),
    ]
