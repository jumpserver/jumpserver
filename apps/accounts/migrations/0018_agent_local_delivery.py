from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0017_application_commands')]
    operations = [migrations.AddField(
        model_name='credentialclientinstance', name='restart_supported',
        field=models.BooleanField(default=False),
    )]
