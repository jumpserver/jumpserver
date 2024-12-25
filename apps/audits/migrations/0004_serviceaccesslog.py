# Generated by Django 4.1.13 on 2024-11-28 09:48

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('audits', '0003_auto_20180816_1652'),
    ]

    operations = [
        migrations.CreateModel(
            name='ServiceAccessLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('remote_addr', models.GenericIPAddressField(verbose_name='Remote addr')),
                ('service', models.CharField(max_length=128, verbose_name='Application')),
                ('service_id', models.UUIDField(verbose_name='Application ID')),
                ('asset', models.CharField(max_length=128, verbose_name='Asset')),
                ('account', models.CharField(max_length=128, verbose_name='Account')),
                ('datetime', models.DateTimeField(auto_now=True, verbose_name='Datetime')),
            ],
        ),
    ]