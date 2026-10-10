from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('audits', '0009_alter_passwordchangelog_datetime'),
        ('tickets', '0009_ticketassignee_assignee_display_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='TicketAudit',
            fields=[],
            options={
                'verbose_name': 'Ticket audit',
                'proxy': True,
                'default_permissions': ('view',),
                'indexes': [],
                'constraints': [],
            },
            bases=('tickets.ticket',),
        ),
    ]
