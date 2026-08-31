from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('perms', '0003_alter_assetpermission_date_expired'),
    ]

    operations = [
        migrations.AddField(
            model_name='assetpermission',
            name='short_expire_notice_enabled',
            field=models.BooleanField(default=False, verbose_name='Short expiration notice enabled'),
        ),
        migrations.AddField(
            model_name='assetpermission',
            name='short_expire_notice_minutes',
            field=models.PositiveIntegerField(
                blank=True, null=True, verbose_name='Short expiration notice minutes'
            ),
        ),
        migrations.AddField(
            model_name='assetpermission',
            name='short_expire_notice_at',
            field=models.DateTimeField(
                blank=True, db_index=True, null=True, verbose_name='Short expiration notice time'
            ),
        ),
        migrations.AddField(
            model_name='assetpermission',
            name='short_expire_notice_sent_at',
            field=models.DateTimeField(
                blank=True, null=True, verbose_name='Short expiration notice sent time'
            ),
        ),
    ]
