# Generated by Django 4.1.13 on 2025-04-15 11:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0018_asset_directory_services"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="platform",
            name="ds",
        ),
    ]
