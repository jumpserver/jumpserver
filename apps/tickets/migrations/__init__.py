# Generated by Django 3.1.6 on 2021-08-10 15:25

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import tickets.models.ticket
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tickets', '0009_auto_20210426_1720'),
    ]

    operations = [
        migrations.CreateModel(
            name='Template',
            fields=[
                ('org_id', models.CharField(blank=True, db_index=True, default='', max_length=36, verbose_name='Organization')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('created_by', models.CharField(blank=True, max_length=32, null=True, verbose_name='Created by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('title', models.CharField(max_length=256, verbose_name='Title')),
                ('type', models.CharField(choices=[('general', 'General'), ('login_confirm', 'Login confirm'), ('apply_asset', 'Apply for asset'), ('apply_application', 'Apply for application'), ('login_asset_confirm', 'Login asset confirm'), ('command_confirm', 'Command confirm')], default='general', max_length=64, verbose_name='Type')),
            ],
            options={
                'verbose_name': 'Ticket template',
            },
        ),
        migrations.RemoveField(
            model_name='ticket',
            name='assignees_display',
        ),
        migrations.RemoveField(
            model_name='ticket',
            name='processor',
        ),
        migrations.RemoveField(
            model_name='ticket',
            name='processor_display',
        ),
        migrations.AddField(
            model_name='ticket',
            name='approve_level',
            field=models.SmallIntegerField(default=1, verbose_name='Approve level'),
        ),
        migrations.AddField(
            model_name='ticket',
            name='process',
            field=models.JSONField(default=list, encoder=tickets.models.ticket.ModelJSONFieldEncoder, verbose_name='Process'),
        ),
        migrations.AddField(
            model_name='ticketassignees',
            name='approve_level',
            field=models.SmallIntegerField(choices=[(1, 'One level'), (2, 'Two level')], default=1, verbose_name='Approve level'),
        ),
        migrations.AddField(
            model_name='ticketassignees',
            name='action',
            field=models.CharField(choices=[('open', 'Open'), ('approve', 'Approve'), ('reject', 'Reject'), ('close', 'Close')], default='open', max_length=16, verbose_name='Action'),
        ),
        migrations.AddField(
            model_name='ticketassignees',
            name='is_processor',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='ticketassignees',
            name='created_by',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Created by'),
        ),
        migrations.AddField(
            model_name='ticketassignees',
            name='date_created',
            field=models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created'),
        ),
        migrations.AddField(
            model_name='ticketassigneesqZx',
            name='date_updated',
            field=models.DateTimeField(auto_now=True, verbose_name='Date updated'),
        ),
        migrations.CreateModel(
            name='TemplateApprove',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('created_by', models.CharField(blank=True, max_length=32, null=True, verbose_name='Created by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('approve_level', models.SmallIntegerField(choices=[(1, 'One level'), (2, 'Two level')], default=1, verbose_name='Approve level')),
                ('approve_strategy', models.CharField(choices=[('super', 'Super user'), ('super_admin', 'Super admin user'), ('all_user', 'All user')], default='super_admin', max_length=64, verbose_name='Approve strategy')),
                ('assignees_display', models.JSONField(default=list, encoder=tickets.models.ticket.ModelJSONFieldEncoder, verbose_name='Assignees display')),
                ('assignees', models.ManyToManyField(related_name='assigned_template_approve', to=settings.AUTH_USER_MODEL, verbose_name='Assignees')),
                ('ticket_template', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='templated_approves', to='tickets.template', verbose_name='Template')),
            ],
            options={
                'verbose_name': 'Ticket template approve level',
            },
        ),
        migrations.AddField(
            model_name='ticket',
            name='template',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='templated_tickets', to='tickets.template', verbose_name='Template'),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='assignees',
            field=models.ManyToManyField(related_name='assigned_tickets', through='tickets.TicketAssignee', to=settings.AUTH_USER_MODEL, verbose_name='Assignees'),
        ),
    ]
