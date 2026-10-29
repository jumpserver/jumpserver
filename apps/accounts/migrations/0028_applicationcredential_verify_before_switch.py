from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0027_pam_agent_display_name')]

    operations = [
        migrations.AddField(
            model_name='applicationcredential', name='verify_before_switch',
            field=models.BooleanField(
                default=True, verbose_name='Verify backup account before switching',
                help_text='Verify the backup account from the server before switching. '
                          'When disabled, ensure the backup account is usable yourself.',
            ),
        ),
    ]
