from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('perms', '0006_assetpermission_expire_soon_notice')]

    operations = [
        migrations.AddField(
            model_name='assetpermission', name='auto_push_same_name',
            field=models.BooleanField(
                default=False, verbose_name='Auto push same-name account on first connection',
            ),
        ),
    ]
