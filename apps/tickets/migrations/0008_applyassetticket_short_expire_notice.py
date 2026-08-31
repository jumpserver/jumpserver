from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0007_ticketflow_name_and_five_approval_levels'),
    ]

    operations = [
        migrations.AddField(
            model_name='applyassetticket',
            name='apply_short_expire_notice_enabled',
            field=models.BooleanField(default=False, verbose_name='Short expiration notice enabled'),
        ),
        migrations.AddField(
            model_name='applyassetticket',
            name='apply_short_expire_notice_minutes',
            field=models.PositiveIntegerField(
                blank=True, null=True, verbose_name='Short expiration notice minutes'
            ),
        ),
    ]
