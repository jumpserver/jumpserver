# Generated by Django 3.1.14 on 2022-06-09 09:58
from datetime import datetime
from collections import defaultdict

from django.conf import settings
from django.utils import timezone as dj_timezone
from django.db import migrations, models
import django.db.models.deletion

from tickets.const import TicketType
from assets.models import Node, Asset, SystemUser, CommandFilterRule, CommandFilter
from applications.models import Application
from perms.models import Action
from terminal.models import Session


def time_conversion(t):
    if not t:
        return
    try:
        return datetime.strptime(t, '%Y-%m-%d %H:%M:%S'). \
            astimezone(dj_timezone.get_current_timezone())
    except Exception:
        return


nodes_dict = defaultdict(set)
assets_dict = defaultdict(set)
system_users_dict = defaultdict(set)
apps_dict = defaultdict(set)

node_qs = Node.objects.values('id', 'org_id')
asset_qs = Asset.objects.values('id', 'org_id')
system_user_qs = SystemUser.objects.values('id', 'org_id')
app_qs = Application.objects.values('id', 'org_id')

for d, qs in [
    (nodes_dict, node_qs),
    (assets_dict, asset_qs),
    (system_users_dict, system_user_qs),
    (apps_dict, app_qs)]:
    for i in qs:
        _id = str(i['id'])
        org_id = str(i['org_id'])
        d[org_id].add(_id)


def apply_asset_migrate(apps):
    ticket_model = apps.get_model('tickets', 'Ticket')
    tickets = ticket_model.objects.filter(type=TicketType.apply_asset)
    ticket_apply_asset_model = apps.get_model('tickets', 'ApplyAssetTicket')
    for instance in tickets:
        meta = instance.meta
        org_id = instance.org_id
        data = {
            'ticket_ptr_id': instance.pk,
            'apply_permission_name': meta.get('apply_permission_name', ''),
            'apply_date_start': time_conversion(meta.get('apply_date_start')),
            'apply_date_expired': time_conversion(meta.get('apply_date_expired')),
            'apply_actions': Action.choices_to_value(value=meta.get('apply_actions', [])),
        }
        apply_nodes = list(set(meta.get('apply_nodes', [])) & nodes_dict.get(org_id, set()))
        apply_assets = list(set(meta.get('apply_assets', [])) & assets_dict.get(org_id, set()))
        apply_system_users = list(set(meta.get('apply_system_users', [])) & system_users_dict.get(org_id, set()))
        rel_snapshot = {
            'applicant': instance.applicant_display,
            'apply_nodes': meta.get('apply_nodes_display', []),
            'apply_assets': meta.get('apply_assets_display', []),
            'apply_system_users': meta.get('apply_system_users', []),
        }
        instance.rel_snapshot = rel_snapshot
        instance.save()
        child = ticket_apply_asset_model(**data)
        child.__dict__.update(instance.__dict__)
        child.save()
        child.apply_nodes.set(apply_nodes)
        child.apply_assets.set(apply_assets)
        child.apply_system_users.set(apply_system_users)


def apply_application_migrate(apps):
    ticket_model = apps.get_model('tickets', 'Ticket')
    tickets = ticket_model.objects.filter(type=TicketType.apply_application)
    ticket_apply_app_model = apps.get_model('tickets', 'ApplyApplicationTicket')
    for instance in tickets:
        meta = instance.meta
        org_id = instance.org_id
        data = {
            'ticket_ptr_id': instance.id,
            'apply_permission_name': meta.get('apply_permission_name', ''),
            'apply_category': meta.get('apply_category'),
            'apply_type': meta.get('apply_type'),
            'apply_date_start': time_conversion(meta.get('apply_date_start')),
            'apply_date_expired': time_conversion(meta.get('apply_date_expired')),
        }
        apply_applications = list(set(meta.get('apply_applications', [])) & apps_dict.get(org_id, set()))
        apply_system_users = list(set(meta.get('apply_system_users', [])) & system_users_dict.get(org_id, set()))
        rel_snapshot = {
            'applicant': instance.applicant_display,
            'apply_applications': meta.get('apply_applications_display', []),
            'apply_system_users': meta.get('apply_system_users', []),
        }
        instance.rel_snapshot = rel_snapshot
        instance.save()
        child = ticket_apply_app_model(**data)
        child.__dict__.update(instance.__dict__)
        child.save()
        child.apply_applications.set(apply_applications)
        child.apply_system_users.set(apply_system_users)


def login_confirm_migrate(apps):
    ticket_model = apps.get_model('tickets', 'Ticket')
    tickets = ticket_model.objects.filter(type=TicketType.login_confirm)
    ticket_apply_login_model = apps.get_model('tickets', 'ApplyLoginTicket')

    for instance in tickets:
        meta = instance.meta
        data = {
            'ticket_ptr_id': instance.id,
            'apply_login_ip': meta.get('apply_login_ip'),
            'apply_login_city': meta.get('apply_login_city'),
            'apply_login_datetime': time_conversion(meta.get('apply_login_datetime')),
        }
        rel_snapshot = {
            'applicant': instance.applicant_display
        }
        instance.rel_snapshot = rel_snapshot
        instance.save()
        child = ticket_apply_login_model(**data)
        child.__dict__.update(instance.__dict__)
        child.save()


def analysis_instance_name(name: str):
    if not name:
        return
    name, username = name.split('(', 1)
    return name, username[:-1]


def login_asset_confirm_migrate(apps):
    user_model = apps.get_model('users', 'User')
    asset_model = apps.get_model('assets', 'Asset')
    system_user_model = apps.get_model('assets', 'SystemUser')
    ticket_model = apps.get_model('tickets', 'Ticket')
    tickets = ticket_model.objects.filter(type=TicketType.login_asset_confirm)
    ticket_apply_login_asset_model = apps.get_model('tickets', 'ApplyLoginAssetTicket')
    for instance in tickets:
        meta = instance.meta
        try:
            apply_login_user_name = analysis_instance_name(meta.get('apply_login_user'))
            apply_login_user = user_model.objects.filter(
                name=apply_login_user_name[0], username=apply_login_user_name[1][:-1]
            ).first() if apply_login_user_name else None

            apply_login_asset_name = analysis_instance_name(meta.get('apply_login_asset'))
            apply_login_asset = asset_model.objects.filter(
                hostname=apply_login_asset_name[0], ip=apply_login_asset_name[1][:-1]
            ).first() if apply_login_asset_name else None

            apply_login_system_user_name = analysis_instance_name(meta.get('apply_login_system_user'))
            apply_login_system_user = system_user_model.objects.filter(
                name=apply_login_system_user_name[0], username=apply_login_system_user_name[1][:-1]
            ).first() if apply_login_system_user_name else None
        except Exception as e:
            instance.delete()
            continue
        data = {
            'ticket_ptr_id': instance.id,
            'apply_login_user': apply_login_user,
            'apply_login_asset': apply_login_asset,
            'apply_login_system_user': apply_login_system_user,
        }
        rel_snapshot = {
            'applicant': instance.applicant_display,
            'apply_login_user': meta.get('apply_login_user', ''),
            'apply_login_asset': meta.get('apply_login_asset', ''),
            'apply_login_system_user': meta.get('apply_login_system_user', ''),
        }
        instance.rel_snapshot = rel_snapshot
        instance.save()
        child = ticket_apply_login_asset_model(**data)
        child.__dict__.update(instance.__dict__)
        child.save()


def command_confirm_migrate(apps):
    user_model = apps.get_model('users', 'User')
    asset_model = apps.get_model('assets', 'Asset')
    system_user_model = apps.get_model('assets', 'SystemUser')
    ticket_model = apps.get_model('tickets', 'Ticket')
    tickets = ticket_model.objects.filter(type=TicketType.command_confirm)
    session_ids = [str(i) for i in Session.objects.values_list('id', flat=True)]
    command_filter_ids = [str(i) for i in CommandFilter.objects.values_list('id', flat=True)]
    command_filter_rule_ids = [str(i) for i in CommandFilterRule.objects.values_list('id', flat=True)]
    ticket_apply_command_model = apps.get_model('tickets', 'ApplyCommandTicket')
    for instance in tickets:
        meta = instance.meta
        try:
            apply_run_user_name = analysis_instance_name(meta.get('apply_run_user'))
            apply_run_user = user_model.objects.filter(
                name=apply_run_user_name[0], username=apply_run_user_name[1][:-1]
            ).first() if apply_run_user_name else None

            apply_run_asset_name = analysis_instance_name(meta.get('apply_run_asset'))
            apply_run_asset = asset_model.objects.filter(
                hostname=apply_run_asset_name[0], ip=apply_run_asset_name[1][:-1]
            ).first() if apply_run_asset_name else None

            apply_run_system_user_name = analysis_instance_name(meta.get('apply_run_system_user'))
            apply_run_system_user = system_user_model.objects.filter(
                name=apply_run_system_user_name[0], username=apply_run_system_user_name[1][:-1]
            ).first() if apply_run_system_user_name else None
        except Exception as e:
            instance.delete()
            continue
        apply_from_session_id = meta.get('apply_from_session_id')
        apply_from_cmd_filter_id = meta.get('apply_from_cmd_filter_id')
        apply_from_cmd_filter_rule_id = meta.get('apply_from_cmd_filter_rule_id')
        if apply_from_session_id not in session_ids or \
                apply_from_cmd_filter_id not in command_filter_ids or \
                apply_from_cmd_filter_rule_id not in command_filter_rule_ids:
            instance.delete()
            continue
        data = {
            'ticket_ptr_id': instance.id,
            'apply_run_user': apply_run_user,
            'apply_run_asset': apply_run_asset,
            'apply_run_system_user': apply_run_system_user,
            'apply_run_command': meta.get('apply_run_command', ''),
            'apply_from_session_id': meta.get('apply_from_session_id'),
            'apply_from_cmd_filter_id': meta.get('apply_from_cmd_filter_id'),
            'apply_from_cmd_filter_rule_id': meta.get('apply_from_cmd_filter_rule_id'),
        }

        rel_snapshot = {
            'applicant': instance.applicant_display,
            'apply_run_user': meta.get('apply_run_user', ''),
            'apply_run_asset': meta.get('apply_run_asset', ''),
            'apply_run_system_user': meta.get('apply_run_system_user', ''),
            'apply_from_session': meta.get('apply_from_session_id', ''),
            'apply_from_cmd_filter': meta.get('apply_from_cmd_filter_id', ''),
            'apply_from_cmd_filter_rule': meta.get('apply_from_cmd_filter_rule_id', ''),
        }
        instance.rel_snapshot = rel_snapshot
        instance.save()
        child = ticket_apply_command_model(**data)
        child.__dict__.update(instance.__dict__)
        child.save()


def restructure_migrate(apps, schema_editor):
    ticket_model = apps.get_model('tickets', 'Ticket')
    ticket_step_model = apps.get_model('tickets', 'TicketStep')
    ticket_assignee_model = apps.get_model('tickets', 'TicketAssignee')
    ticket_model.objects.filter(state='open').update(state='pending')
    ticket_step_model.objects.filter(state='notified').update(state='pending')
    ticket_assignee_model.objects.filter(state='notified').update(state='pending')
    apply_asset_migrate(apps)
    apply_application_migrate(apps)
    login_confirm_migrate(apps)
    login_asset_confirm_migrate(apps)
    command_confirm_migrate(apps)



class Migration(migrations.Migration):
    dependencies = [
        ('terminal', '0049_endpoint_redis_port'),
        ('assets', '0090_auto_20220412_1145'),
        ('applications', '0020_auto_20220316_2028'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tickets', '0015_superticket'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApplyLoginTicket',
            fields=[
                ('ticket_ptr',
                 models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True,
                                      primary_key=True, serialize=False, to='tickets.ticket')),
                ('apply_login_ip', models.GenericIPAddressField(null=True, verbose_name='Login ip')),
                ('apply_login_city', models.CharField(max_length=64, null=True, verbose_name='Login city')),
                ('apply_login_datetime', models.DateTimeField(null=True, verbose_name='Login datetime')),
            ],
            options={
                'abstract': False,
            },
            bases=('tickets.ticket',),
        ),
        migrations.RemoveField(
            model_name='ticket',
            name='process_map',
        ),
        migrations.AddField(
            model_name='comment',
            name='state',
            field=models.CharField(max_length=16, null=True),
        ),
        migrations.AddField(
            model_name='comment',
            name='type',
            field=models.CharField(choices=[('state', 'State'), ('common', 'common')], default='common', max_length=16,
                                   verbose_name='Type'),
        ),
        migrations.AddField(
            model_name='ticket',
            name='rel_snapshot',
            field=models.JSONField(default=dict, verbose_name='Relation snapshot'),
        ),
        migrations.AddField(
            model_name='ticketstep',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('active', 'Active'), ('closed', 'Closed')],
                                   default='pending', max_length=16),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='state',
            field=models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
                                            ('closed', 'Cancel'), ('reopen', 'Reopen')], default='pending',
                                   max_length=16, verbose_name='State'),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='status',
            field=models.CharField(choices=[('open', 'Open'), ('closed', 'Finished')], default='open', max_length=16,
                                   verbose_name='Status'),
        ),
        migrations.AlterField(
            model_name='ticketassignee',
            name='state',
            field=models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
                                            ('closed', 'Cancel'), ('reopen', 'Reopen')], default='pending',
                                   max_length=64),
        ),
        migrations.AlterField(
            model_name='ticketstep',
            name='state',
            field=models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
                                            ('closed', 'Closed')], default='pending', max_length=64,
                                   verbose_name='State'),
        ),
        migrations.CreateModel(
            name='ApplyLoginAssetTicket',
            fields=[
                ('ticket_ptr',
                 models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True,
                                      primary_key=True, serialize=False, to='tickets.ticket')),
                ('apply_login_asset',
                 models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='assets.asset',
                                   verbose_name='Login asset')),
                ('apply_login_system_user',
                 models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='assets.systemuser',
                                   verbose_name='Login system user')),
                ('apply_login_user',
                 models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL,
                                   verbose_name='Login user')),
            ],
            options={
                'abstract': False,
            },
            bases=('tickets.ticket',),
        ),
        migrations.CreateModel(
            name='ApplyCommandTicket',
            fields=[
                ('ticket_ptr',
                 models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True,
                                      primary_key=True, serialize=False, to='tickets.ticket')),
                ('apply_run_command', models.CharField(max_length=4096, verbose_name='Run command')),
                ('apply_from_cmd_filter',
                 models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='assets.commandfilter',
                                   verbose_name='From cmd filter')),
                ('apply_from_cmd_filter_rule',
                 models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                                   to='assets.commandfilterrule', verbose_name='From cmd filter rule')),
                ('apply_from_session',
                 models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='terminal.session',
                                   verbose_name='Session')),
                ('apply_run_asset',
                 models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='assets.asset',
                                   verbose_name='Run asset')),
                ('apply_run_system_user',
                 models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='assets.systemuser',
                                   verbose_name='Run system user')),
                ('apply_run_user',
                 models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL,
                                   verbose_name='Run user')),
            ],
            options={
                'abstract': False,
            },
            bases=('tickets.ticket',),
        ),
        migrations.CreateModel(
            name='ApplyAssetTicket',
            fields=[
                ('ticket_ptr',
                 models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True,
                                      primary_key=True, serialize=False, to='tickets.ticket')),
                ('apply_permission_name', models.CharField(max_length=128, verbose_name='Apply name')),
                ('apply_actions', models.IntegerField(
                    choices=[(255, 'All'), (1, 'Connect'), (2, 'Upload file'), (4, 'Download file'),
                             (6, 'Upload download'), (8, 'Clipboard copy'), (16, 'Clipboard paste'),
                             (24, 'Clipboard copy paste')], default=255, verbose_name='Actions')),
                ('apply_date_start', models.DateTimeField(null=True, verbose_name='Date start')),
                ('apply_date_expired', models.DateTimeField(null=True, verbose_name='Date expired')),
                ('apply_assets', models.ManyToManyField(to='assets.Asset', verbose_name='Apply assets')),
                ('apply_nodes', models.ManyToManyField(to='assets.Node', verbose_name='Apply nodes')),
                ('apply_system_users',
                 models.ManyToManyField(to='assets.SystemUser', verbose_name='Apply system users')),
            ],
            options={
                'abstract': False,
            },
            bases=('tickets.ticket',),
        ),
        migrations.CreateModel(
            name='ApplyApplicationTicket',
            fields=[
                ('ticket_ptr',
                 models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True,
                                      primary_key=True, serialize=False, to='tickets.ticket')),
                ('apply_permission_name', models.CharField(max_length=128, verbose_name='Apply name')),
                ('apply_category',
                 models.CharField(choices=[('db', 'Database'), ('remote_app', 'Remote app'), ('cloud', 'Cloud')],
                                  max_length=16, verbose_name='Category')),
                ('apply_type', models.CharField(
                    choices=[('mysql', 'MySQL'), ('mariadb', 'MariaDB'), ('oracle', 'Oracle'),
                             ('postgresql', 'PostgreSQL'), ('sqlserver', 'SQLServer'), ('redis', 'Redis'),
                             ('mongodb', 'MongoDB'), ('chrome', 'Chrome'), ('mysql_workbench', 'MySQL Workbench'),
                             ('vmware_client', 'vSphere Client'), ('custom', 'Custom'), ('k8s', 'Kubernetes')],
                    max_length=16, verbose_name='Type')),
                ('apply_date_start', models.DateTimeField(null=True, verbose_name='Date start')),
                ('apply_date_expired', models.DateTimeField(null=True, verbose_name='Date expired')),
                ('apply_applications',
                 models.ManyToManyField(to='applications.Application', verbose_name='Apply applications')),
                ('apply_system_users',
                 models.ManyToManyField(to='assets.SystemUser', verbose_name='Apply system users')),
            ],
            options={
                'abstract': False,
            },
            bases=('tickets.ticket',),
        ),
        migrations.RunPython(restructure_migrate),
        migrations.RemoveField(
            model_name='ticket',
            name='meta',
        ),
        migrations.RemoveField(
            model_name='ticket',
            name='applicant_display',
        ),
    ]
