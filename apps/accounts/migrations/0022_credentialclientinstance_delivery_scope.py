from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0021_application_account_scope_limit')]

    operations = [
        migrations.AddField(
            model_name='credentialclientinstance', name='delivery_scope',
            field=models.JSONField(blank=True, default=None, null=True),
        ),
    ]
