from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('assets', '0020_favoritefolder'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='date_last_login',
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                null=True,
                verbose_name='Last login time',
            ),
        ),
    ]
