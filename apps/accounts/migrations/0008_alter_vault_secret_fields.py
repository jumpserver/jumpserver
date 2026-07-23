from django.db import migrations

import accounts.models.mixins.vault


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_alter_account_connectivity'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='_secret',
            field=accounts.models.mixins.vault.VaultSecretField(
                blank=True, null=True, verbose_name='Secret'
            ),
        ),
        migrations.AlterField(
            model_name='accounttemplate',
            name='_secret',
            field=accounts.models.mixins.vault.VaultSecretField(
                blank=True, null=True, verbose_name='Secret'
            ),
        ),
        migrations.AlterField(
            model_name='historicalaccount',
            name='_secret',
            field=accounts.models.mixins.vault.VaultSecretField(
                blank=True, null=True, verbose_name='Secret'
            ),
        ),
    ]
