# Generated by Django 3.1.13 on 2022-01-12 11:59

import common.db.encoder
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('assets', '0083_auto_20211215_1436'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccountBackupPlan',
            fields=[
                ('org_id', models.CharField(blank=True, db_index=True, default='', max_length=36, verbose_name='Organization')),
                ('name', models.CharField(max_length=128, verbose_name='Name')),
                ('is_periodic', models.BooleanField(default=False, verbose_name='Periodic perform')),
                ('interval', models.IntegerField(blank=True, default=24, null=True, verbose_name='Interval')),
                ('crontab', models.CharField(blank=True, max_length=128, null=True, verbose_name='Crontab')),
                ('created_by', models.CharField(blank=True, max_length=32, null=True, verbose_name='Created by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('types', models.IntegerField(choices=[(255, 'All'), (1, 'Asset'), (2, 'Application')], default=255, verbose_name='Type')),
                ('comment', models.TextField(blank=True, verbose_name='Comment')),
                ('recipients', models.ManyToManyField(blank=True, related_name='recipient_escape_route_plans', to=settings.AUTH_USER_MODEL, verbose_name='Recipient')),
            ],
            options={
                'verbose_name': 'Account backup plan',
                'ordering': ['name'],
                'unique_together': {('name', 'org_id')},
            },
        ),
        migrations.AlterField(
            model_name='systemuser',
            name='protocol',
            field=models.CharField(choices=[('ssh', 'SSH'), ('rdp', 'RDP'), ('telnet', 'Telnet'), ('vnc', 'VNC'), ('mysql', 'MySQL'), ('redis', 'Redis'), ('oracle', 'Oracle'), ('mariadb', 'MariaDB'), ('postgresql', 'PostgreSQL'), ('sqlserver', 'SQLServer'), ('k8s', 'K8s')], default='ssh', max_length=16, verbose_name='Protocol'),
        ),
        migrations.CreateModel(
            name='AccountBackupPlanExecution',
            fields=[
                ('org_id', models.CharField(blank=True, db_index=True, default='', max_length=36, verbose_name='Organization')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('date_start', models.DateTimeField(auto_now_add=True, verbose_name='Date start')),
                ('timedelta', models.FloatField(default=0.0, null=True, verbose_name='Time')),
                ('plan_snapshot', models.JSONField(blank=True, default=dict, encoder=common.db.encoder.ModelJSONFieldEncoder, null=True, verbose_name='Account backup snapshot')),
                ('trigger', models.CharField(choices=[('manual', 'Manual trigger'), ('timing', 'Timing trigger')], default='manual', max_length=128, verbose_name='Trigger mode')),
                ('reason', models.CharField(blank=True, max_length=1024, null=True, verbose_name='Reason')),
                ('is_success', models.BooleanField(default=False, verbose_name='Is success')),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='execution', to='assets.accountbackupplan', verbose_name='Account backup plan')),
            ],
            options={
                'verbose_name': 'Account backup execution',
            },
        ),
    ]
