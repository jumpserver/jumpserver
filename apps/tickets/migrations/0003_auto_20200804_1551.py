from django.conf import settings
from django.db import migrations

ticket_assignee_m2m = list()


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tickets', '0002_auto_20200728_1146'),
    ]

    operations = [
    ]
