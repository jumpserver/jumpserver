# Generated by Django 3.2.14 on 2022-09-30 09:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0091_auto_20220629_1826'),
    ]

    operations = [
        migrations.AlterField(
            model_name='commandfilter',
            name='date_created',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Date created'),
        ),
        migrations.AlterField(
            model_name='commandfilter',
            name='date_updated',
            field=models.DateTimeField(auto_now=True, verbose_name='Date updated'),
        ),
    ]
