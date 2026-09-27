from uuid import UUID

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_beneficiaries(apps, schema_editor):
    db = schema_editor.connection.alias
    Ticket = apps.get_model('tickets', 'Ticket')
    Beneficiary = apps.get_model('tickets', 'TicketBeneficiary')
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))

    def insert(rows):
        ids = {str(user_id) for _, user_id in rows}
        valid = {str(pk) for pk in User.objects.using(db).filter(pk__in=ids).values_list('pk', flat=True)}
        Beneficiary.objects.using(db).bulk_create([
            Beneficiary(ticket_id=ticket_id, user_id=user_id)
            for ticket_id, user_id in rows if str(user_id) in valid
        ], ignore_conflicts=True)

    batch = []
    tickets = Ticket.objects.using(db).filter(type='apply_asset').values('id', 'applicant_id', 'request_data')
    for ticket in tickets.iterator(chunk_size=500):
        users = (ticket['request_data'] or {}).get('apply_users') or [ticket['applicant_id']]
        if not isinstance(users, list):
            continue
        for user_id in users:
            try:
                batch.append((ticket['id'], str(UUID(str(user_id)))))
            except (TypeError, ValueError, AttributeError):
                continue
        if len(batch) >= 500:
            insert(batch)
            batch.clear()
    if batch:
        insert(batch)


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0016_merge_ticket_models'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='workflow',
            options={
                'ordering': ['name', 'id'],
                'verbose_name': 'Approval workflow',
                'default_permissions': ('add', 'change', 'view'),
                'permissions': [('apply_asset_for_others', 'Apply for asset access on behalf of another user')],
            },
        ),
        migrations.CreateModel(
            name='TicketBeneficiary',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                             related_name='beneficiaries', to='tickets.ticket')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                           related_name='benefiting_tickets', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'default_permissions': (), 'verbose_name': 'Ticket beneficiary',
                'unique_together': {('ticket', 'user')},
            },
        ),
        migrations.RunPython(backfill_beneficiaries, migrations.RunPython.noop),
    ]
