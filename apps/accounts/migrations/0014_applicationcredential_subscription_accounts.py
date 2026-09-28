from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0013_application_credentials'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicationcredential',
            name='subscription_accounts',
            field=models.ManyToManyField(
                blank=True, related_name='subscribed_application_credentials',
                to='accounts.account', verbose_name='Subscribed accounts',
            ),
        ),
        # Preserve the scope of policies created before explicit account selection.
        migrations.AddField(
            model_name='applicationcredential',
            name='subscription_all_authorized',
            field=models.BooleanField(default=True, editable=False),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='applicationcredential',
            name='subscription_all_authorized',
            field=models.BooleanField(default=False, editable=False),
        ),
        migrations.AlterField(
            model_name='applicationcredential',
            name='mode',
            field=models.CharField(
                choices=[
                    ('subscription', 'Credential change subscription'),
                    ('alternating_rotation', 'Account rotation'),
                ],
                default='subscription', max_length=32, verbose_name='Mode',
            ),
        ),
    ]
