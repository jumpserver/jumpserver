from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0010_credentialpolicy_credentiallease_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='credentialpolicy',
            name='operation_task_id',
            field=models.CharField(
                blank=True, default='', max_length=255,
                verbose_name='Operation task ID',
            ),
        ),
    ]
