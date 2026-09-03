from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat_ai', '0002_conversation_use_chatai'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='web_search',
            field=models.BooleanField(default=False, verbose_name='Web search'),
        ),
    ]
