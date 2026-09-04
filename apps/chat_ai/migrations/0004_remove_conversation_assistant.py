from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat_ai', '0003_message_web_search'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='conversation',
            name='assistant',
        ),
    ]
