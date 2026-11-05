from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('authentication', '0011_connectiontoken_date_last_used')]
    operations = [
        migrations.AddField(
            model_name='connectiontoken', name='acl_context',
            field=models.JSONField(blank=True, default=dict, verbose_name='Connection ACL context'),
        ),
    ]
