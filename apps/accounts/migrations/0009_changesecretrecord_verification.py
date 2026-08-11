from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_alter_vault_secret_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='changesecretrecord',
            name='account_version',
            field=models.IntegerField(
                blank=True, null=True, verbose_name='Account version'
            ),
        ),
        migrations.AddField(
            model_name='changesecretrecord',
            name='date_verified',
            field=models.DateTimeField(
                blank=True, null=True, verbose_name='Date verified'
            ),
        ),
        migrations.AddField(
            model_name='changesecretrecord',
            name='verification_error',
            field=models.TextField(
                blank=True, default='', verbose_name='Verification error'
            ),
        ),
        migrations.AddField(
            model_name='changesecretrecord',
            name='verification_status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('success', 'Success'),
                    ('failed', 'Failed'),
                    ('pending', 'Pending'),
                    ('unverified', 'Unverified'),
                ],
                default='', max_length=16,
                verbose_name='Verification status',
            ),
        ),
    ]
