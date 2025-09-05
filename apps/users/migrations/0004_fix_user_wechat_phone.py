
from django.db import migrations


def fix_user_wechat_phone(apps, schema_editor):
    User = apps.get_model("users", "User")
    users = User.objects.all()

    for user in users:
        update_fields = []

        if user.wechat and '==' in user.wechat and len(user.wechat) > 40:
            user.wechat = ''
            update_fields.append("wechat")

        if user.phone and '==' in user.phone and len(user.phone) > 40:
            user.phone = ''
            update_fields.append("phone")

        if update_fields:
            user.save(update_fields=update_fields)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_alter_user_date_expired'),
    ]

    operations = [
        migrations.RunPython(fix_user_wechat_phone),
    ]
