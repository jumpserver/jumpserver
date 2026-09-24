from django.db import migrations, models


def mark_legacy_system_tickets(apps, schema_editor):
    # These types were only created by ACL entrypoints before origin was stored.
    Ticket = apps.get_model('tickets', 'Ticket')
    Ticket.objects.using(schema_editor.connection.alias).filter(
        type__in=['login_confirm', 'login_asset_confirm', 'command_confirm'],
    ).update(origin='system')


class Migration(migrations.Migration):
    dependencies = [('tickets', '0014_workflow_cc_nodes')]

    operations = [
        migrations.AddField(
            model_name='ticket', name='origin',
            field=models.CharField(
                choices=[('manual', 'Manual request'), ('system', 'System triggered')],
                default='manual', max_length=16, verbose_name='Ticket origin',
            ),
        ),
        migrations.RunPython(mark_legacy_system_tickets, migrations.RunPython.noop),
    ]
