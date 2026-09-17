from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('terminal', '0011_endpoint_magnus_port')]
    # WebLite replaces the default installation, not administrators' published apps.
    # Keep the migration name for installations that have already applied it.
    operations = []
