from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0020_remove_applicationaudit_configuration_and_more')]

    operations = [
        migrations.AddField(
            model_name='integrationapplication', name='enforce_account_limit',
            field=models.BooleanField(default=False, editable=False),
        ),
        migrations.AlterField(
            model_name='integrationapplication', name='enforce_account_limit',
            field=models.BooleanField(default=True, editable=False),
        ),
    ]
