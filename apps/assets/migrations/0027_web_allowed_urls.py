from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("assets", "0026_web_success_selector")]

    operations = [
        migrations.AddField(
            model_name="web",
            name="allowed_urls",
            field=models.JSONField(blank=True, default=list, verbose_name="Allowed sites"),
        ),
    ]
