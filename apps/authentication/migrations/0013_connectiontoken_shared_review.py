from django.db import migrations, models
import django.db.models.deletion


def guard_shared_ticket_rollback(apps, schema_editor):
    tokens = apps.get_model('authentication', 'ConnectionToken')._base_manager.using(
        schema_editor.connection.alias,
    )
    shared_tickets = tokens.filter(from_ticket__isnull=False).values('from_ticket').annotate(
        token_count=models.Count('pk'),
    ).filter(token_count__gt=1)
    if shared_tickets.exists():
        raise RuntimeError(
            'Cannot restore one-to-one ticket links while shared approval tickets exist. '
            'Restore the pre-upgrade database backup to roll back without losing connections.'
        )


class Migration(migrations.Migration):
    dependencies = [('authentication', '0012_connectiontoken_acl_context')]
    operations = [
        migrations.AlterField(
            model_name='connectiontoken', name='from_ticket',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='connection_tokens', to='tickets.applyloginassetticket',
                verbose_name='From ticket',
            ),
        ),
        migrations.RunPython(migrations.RunPython.noop, guard_shared_ticket_rollback),
    ]
