from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('authentication', '0014_clientloginsession')]

    operations = [
        migrations.AddField(
            model_name='clientloginsession', name='policy_expires_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.RemoveField(model_name='clientloginsession', name='last_activity_at'),
        migrations.AlterField(
            model_name='clientloginsession', name='revoke_reason',
            field=models.CharField(blank=True, default='', max_length=32, choices=[
                ('logout', 'Logout'), ('app_exit', 'Client exit'),
                ('absolute_timeout', 'Maximum login time'),
                ('policy_changed', 'Client login policy changed'),
                ('security_revoke', 'Authorization revoked'),
            ]),
        ),
    ]
