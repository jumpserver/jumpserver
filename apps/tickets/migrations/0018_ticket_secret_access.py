from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('tickets', '0017_single_asset_beneficiary')]

    operations = [
        migrations.CreateModel(
            name='TicketSecretAccess',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('account_id', models.UUIDField()),
                ('user_id', models.UUIDField()),
                ('org_id', models.CharField(max_length=36)),
                ('expires_at', models.DateTimeField()),
                ('is_active', models.BooleanField(default=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                             related_name='secret_accesses', to='tickets.ticket')),
            ],
            options={'default_permissions': ()},
        ),
        migrations.AddConstraint(
            model_name='ticketsecretaccess',
            constraint=models.UniqueConstraint(fields=('ticket', 'account_id'), name='tickets_secret_ticket_account_uniq'),
        ),
        migrations.AddIndex(
            model_name='ticketsecretaccess',
            index=models.Index(fields=['user_id', 'expires_at'], name='tickets_secret_user_expire'),
        ),
    ]
