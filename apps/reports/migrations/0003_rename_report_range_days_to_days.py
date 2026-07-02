from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0002_alter_reportexecution_status'),
    ]

    operations = [
        migrations.RenameField(
            model_name='report',
            old_name='range_days',
            new_name='days',
        ),
        migrations.DeleteModel('ReportSendRecord'),
        migrations.DeleteModel('ReportExecution'),
        migrations.RemoveField(model_name='report', name='recipients'),
        migrations.RemoveField(model_name='report', name='is_periodic'),
        migrations.RemoveField(model_name='report', name='interval'),
        migrations.RemoveField(model_name='report', name='crontab'),
        migrations.RemoveField(model_name='report', name='start_time'),
        migrations.RemoveField(model_name='report', name='date_last_run'),
    ]
