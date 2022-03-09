# Generated by Django 3.1.14 on 2022-03-07 07:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0018_auto_20220223_1539'),
        ('assets', '0088_auto_20220303_1612'),
        ('perms', '0025_auto_20220223_1539'),
    ]

    operations = [
        migrations.CreateModel(
            name='PermedAsset',
            fields=[
            ],
            options={
                'verbose_name': 'Permed asset',
                'permissions': [('view_myassets', 'Can view my assets'), ('connect_myassets', 'Can connect my assets'), ('view_userassets', 'Can view user assets'), ('view_usergroupassets', 'Can view usergroup assets')],
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('assets.asset',),
        ),
    ]
