# Generated by Django 4.1.13 on 2024-12-03 09:23
from datetime import timedelta as dt_timedelta

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import common.db.fields


def migrate_account_backup(apps, schema_editor):
    old_backup_model = apps.get_model('accounts', 'AccountBackupAutomation')
    account_backup_model = apps.get_model('accounts', 'BackupAccountAutomation')
    backup_id_old_new_map = {}
    for backup in old_backup_model.objects.all():
        data = {
            'comment': backup.comment,
            'created_by': backup.created_by,
            'updated_by': backup.updated_by,
            'date_created': backup.date_created,
            'date_updated': backup.date_updated,
            'name': backup.name,
            'interval': backup.interval,
            'crontab': backup.crontab,
            'is_periodic': backup.is_periodic,
            'start_time': backup.start_time,
            'date_last_run': backup.date_last_run,
            'org_id': backup.org_id,
            'type': 'backup_account',
            'types': backup.types,
            'backup_type': backup.backup_type,
            'is_password_divided_by_email': backup.is_password_divided_by_email,
            'is_password_divided_by_obj_storage': backup.is_password_divided_by_obj_storage,
            'zip_encrypt_password': backup.zip_encrypt_password
        }
        obj = account_backup_model.objects.create(**data)
        backup_id_old_new_map[str(backup.id)] = str(obj.id)
        obj.recipients_part_one.set(backup.recipients_part_one.all())
        obj.recipients_part_two.set(backup.recipients_part_two.all())
        obj.obj_recipients_part_one.set(backup.obj_recipients_part_one.all())
        obj.obj_recipients_part_two.set(backup.obj_recipients_part_two.all())

    old_execution_model = apps.get_model('accounts', 'AccountBackupExecution')
    backup_execution_model = apps.get_model('accounts', 'AutomationExecution')

    for execution in old_execution_model.objects.all():
        automation_id = backup_id_old_new_map.get(str(execution.plan_id))
        if not automation_id:
            continue
        data = {
            'automation_id': automation_id,
            'date_start': execution.date_start,
            'duration': int(execution.timedelta),
            'date_finished': execution.date_start + dt_timedelta(seconds=int(execution.timedelta)),
            'snapshot': execution.snapshot,
            'trigger': execution.trigger,
            'status': 'error' if execution.reason == '-' else 'success',
            'org_id': execution.org_id
        }
        backup_execution_model.objects.create(**data)


class Migration(migrations.Migration):
    dependencies = [
        ('assets', '0010_alter_automationexecution_duration'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('terminal', '0003_auto_20171230_0308'),
        ('accounts', '0018_changesecretrecord_ignore_fail_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='BackupAccountAutomation',
            fields=[
                ('baseautomation_ptr',
                 models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True,
                                      primary_key=True, serialize=False, to='assets.baseautomation')),
                ('types', models.JSONField(default=list)),
                ('backup_type',
                 models.CharField(choices=[('email', 'Email'), ('object_storage', 'SFTP')], default='email',
                                  max_length=128, verbose_name='Backup type')),
                ('is_password_divided_by_email', models.BooleanField(default=True, verbose_name='Password divided')),
                ('is_password_divided_by_obj_storage',
                 models.BooleanField(default=True, verbose_name='Password divided')),
                ('zip_encrypt_password', common.db.fields.EncryptCharField(blank=True, max_length=4096, null=True,
                                                                           verbose_name='Zip encrypt password')),
                ('obj_recipients_part_one',
                 models.ManyToManyField(blank=True, related_name='obj_recipient_part_one_plans',
                                        to='terminal.replaystorage', verbose_name='Object storage recipient part one')),
                ('obj_recipients_part_two',
                 models.ManyToManyField(blank=True, related_name='obj_recipient_part_two_plans',
                                        to='terminal.replaystorage', verbose_name='Object storage recipient part two')),
                ('recipients_part_one', models.ManyToManyField(blank=True, related_name='recipient_part_one_plans',
                                                               to=settings.AUTH_USER_MODEL,
                                                               verbose_name='Recipient part one')),
                ('recipients_part_two', models.ManyToManyField(blank=True, related_name='recipient_part_two_plans',
                                                               to=settings.AUTH_USER_MODEL,
                                                               verbose_name='Recipient part two')),
            ],
            options={
                'verbose_name': 'Account backup plan',
            },
            bases=('accounts.accountbaseautomation',),
        ),
        migrations.RunPython(migrate_account_backup),
        migrations.RemoveField(
            model_name='accountbackupexecution',
            name='plan',
        ),
        migrations.DeleteModel(
            name='AccountBackupAutomation',
        ),
        migrations.DeleteModel(
            name='AccountBackupExecution',
        ),
        migrations.RemoveField(
            model_name='gatheredaccount',
            name='authorized_keys',
        ),
        migrations.RemoveField(
            model_name='gatheredaccount',
            name='groups',
        ),
        migrations.RemoveField(
            model_name='gatheredaccount',
            name='sudoers',
        ),
        migrations.AddField(
            model_name='gatheredaccount',
            name='detail',
            field=models.JSONField(blank=True, default=dict, verbose_name='Detail'),
        ),
    ]