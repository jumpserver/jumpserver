# Generated by Django 4.1.13 on 2025-04-01 07:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0015_automationexecution_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='source',
            field=models.CharField(choices=[('cloud_import', 'Cloud import')], default='cloud_import', max_length=128, verbose_name='Source'),
        ),
        migrations.AddField(
            model_name='asset',
            name='status',
            field=models.CharField(choices=[('-', '-'), ('cloud_released', 'Cloud released')], default='-', max_length=128, verbose_name='Status'),
        ),
    ]
