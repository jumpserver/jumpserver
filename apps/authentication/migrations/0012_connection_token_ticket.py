import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('authentication', '0016_clientloginsession_expires_at'),
        ('tickets', '0009_ticketassignee_assignee_display_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='connectiontoken', name='from_ticket',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='connection_tokens', to='tickets.ticket', verbose_name='From ticket',
            ),
        ),
    ]
