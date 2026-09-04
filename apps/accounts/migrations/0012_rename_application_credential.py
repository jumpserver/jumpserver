from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('accounts', '0011_integrationapplication_credential_access_mode_and_more')]

    operations = [
        migrations.RenameModel('CredentialPolicy', 'ApplicationCredential'),
        migrations.RenameField('CredentialApplicationBinding', 'policy', 'credential'),
    ]
