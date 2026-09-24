import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('authentication', '0010_connectiontoken_personal_credential_id'),
        ('tickets', '0015_ticket_origin'),
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
