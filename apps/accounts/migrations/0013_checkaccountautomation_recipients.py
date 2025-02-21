# Generated by Django 4.1.13 on 2024-11-15 03:00

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0012_accountcheckengine_accountcheckautomation_engines"),
    ]

    operations = [
        migrations.AddField(
            model_name="checkaccountautomation",
            name="recipients",
            field=models.ManyToManyField(
                blank=True, to=settings.AUTH_USER_MODEL, verbose_name="Recipient"
            ),
        ),
    ]
