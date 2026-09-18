from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0007_ticketflow_name_and_five_approval_levels'),
    ]

    operations = [
        migrations.AddField(
            model_name='applyassetticket',
            name='apply_expire_soon_notice_minutes',
            field=models.PositiveIntegerField(
                blank=True, null=True, verbose_name='Expiration-soon notice minutes'
            ),
        ),
    ]
