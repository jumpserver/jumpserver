# Generated by Django 4.1.10 on 2023-07-31 10:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('terminal', '0064_auto_20230728_1001'),
    ]

    operations = [
        migrations.AddField(
            model_name='session',
            name='cmd_amount',
            field=models.IntegerField(default=0, verbose_name='Command amount'),
        ),
    ]
