from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0012_account_follow_template'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AccountProvisioning',
            fields=[
                ('account', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE, primary_key=True,
                    related_name='provisioning', serialize=False, to='accounts.account',
                )),
                ('protocol', models.CharField(max_length=16)),
                ('status', models.CharField(default='queued', max_length=16)),
                ('date_updated', models.DateTimeField(auto_now=True)),
                ('execution', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    to='accounts.automationexecution',
                )),
                ('user', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'First-login account provisioning',
                'default_permissions': (),
            },
        ),
    ]
