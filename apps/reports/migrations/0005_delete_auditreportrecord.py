from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0004_auditreportrecord'),
    ]

    operations = [
        migrations.DeleteModel(
            name='AuditReportRecord',
        ),
    ]
