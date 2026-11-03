# Intentionally duplicates 0015 to verify the PR check. Test only; do not merge.
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('authentication', '0014_clientloginsession')]
    operations = []
