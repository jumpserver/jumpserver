from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0025_credentialclientinstance_remote_addr')]

    operations = [
        migrations.AddField(
            model_name='integrationapplication', name='credential_notifications_enabled',
            field=models.BooleanField(
                default=False, verbose_name='Account credential change notifications',
                help_text='Notify clients when any authorized account credential changes. Client configuration controls local updates.',
            ),
        ),
        migrations.AddField(
            model_name='credentialrotationevent', name='notification_enabled',
            field=models.BooleanField(default=True),
        ),
    ]
