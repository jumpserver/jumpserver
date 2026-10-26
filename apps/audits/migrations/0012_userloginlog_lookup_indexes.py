from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('audits', '0011_alter_ftplog_operate'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='userloginlog',
            index=models.Index(
                fields=['username', 'datetime'], name='login_log_username_date_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='userloginlog',
            index=models.Index(
                fields=['username', 'status', 'city', 'datetime'],
                name='login_log_username_city_idx',
            ),
        ),
    ]
