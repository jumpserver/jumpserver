import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('authentication', '0011_connectiontoken_date_last_used'),
        ('tickets', '0009_ticketassignee_assignee_display_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='connectiontoken', name='from_ticket',
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='connection_token', to='tickets.ticket', verbose_name='From ticket',
            ),
        ),
    ]
