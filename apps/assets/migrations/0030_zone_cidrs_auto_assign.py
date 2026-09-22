from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('assets', '0029_add_virtual_app_host_platform'),
    ]

    operations = [
        migrations.AddField(
            model_name='zone',
            name='cidrs',
            field=models.JSONField(blank=True, default=list, verbose_name='CIDR ranges'),
        ),
        migrations.AddField(
            model_name='zone',
            name='auto_assign',
            field=models.BooleanField(default=False, verbose_name='Auto assign new assets'),
        ),
    ]
