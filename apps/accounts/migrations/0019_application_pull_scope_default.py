from django.db import migrations

from accounts.models.application import empty_application_accounts
from common.db.fields import JSONManyToManyField


def preserve_implicit_all(apps, schema_editor):
    application = apps.get_model('accounts', 'IntegrationApplication')
    application._base_manager.filter(accounts={}).update(accounts={'type': 'all'})


class Migration(migrations.Migration):
    dependencies = [('accounts', '0018_agent_local_delivery')]

    operations = [
        migrations.RunPython(preserve_implicit_all, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='integrationapplication', name='accounts',
            field=JSONManyToManyField(
                'accounts.Account', default=empty_application_accounts,
                allow_empty_ids=True, verbose_name='Accounts',
            ),
        ),
    ]
