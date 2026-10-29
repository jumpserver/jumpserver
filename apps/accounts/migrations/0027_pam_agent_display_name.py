from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0026_application_credential_notifications')]

    operations = [
        migrations.AlterField(
            model_name='credentialclientinstance', name='type',
            field=models.CharField(
                max_length=16, choices=[('sdk', 'SDK'), ('agent', 'PAM Agent')],
                verbose_name='Type',
            ),
        ),
    ]
