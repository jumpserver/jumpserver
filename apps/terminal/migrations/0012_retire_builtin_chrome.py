from django.db import migrations


def retire_chrome(apps, schema_editor):
    # Keep publications and configuration for administrators migrating old hosts.
    Applet = apps.get_model('terminal', 'Applet')
    Applet.objects.filter(name='chrome', builtin=True).update(is_active=False)


class Migration(migrations.Migration):
    dependencies = [('terminal', '0011_endpoint_magnus_port')]
    operations = [migrations.RunPython(retire_chrome, migrations.RunPython.noop)]
