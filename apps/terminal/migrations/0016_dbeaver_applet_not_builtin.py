from django.db import migrations


def mark_dbeaver_as_not_builtin(apps, schema_editor):
    """
    DBeaver 不再内置，源码目录已删除。存量环境里的记录改为非内置后，
    读取 README、下发应用包等都会落到 media 下的副本上，老环境继续可用；
    新安装的环境没有这条记录，只有 DBX
    """
    applet_model = apps.get_model('terminal', 'Applet')
    applet_model.objects.filter(name='dbeaver', builtin=True).update(builtin=False)


class Migration(migrations.Migration):
    dependencies = [
        ('terminal', '0015_sessionjoinrecord_joiner_display_and_more'),
    ]

    operations = [
        migrations.RunPython(mark_dbeaver_as_not_builtin, migrations.RunPython.noop),
    ]
