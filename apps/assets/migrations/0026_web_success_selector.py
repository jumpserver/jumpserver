from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assets", "0025_node_tree_pagination_index"),
    ]

    operations = [
        migrations.AddField(
            model_name="web",
            name="success_selector",
            field=models.CharField(
                blank=True,
                default='',
                max_length=128,
                verbose_name='Success selector',
                help_text='Selector for an element that appears only after a successful login, e.g. css=#dashboard. Required for basic autofill.',
            ),
        ),
        migrations.AddField(
            model_name="web",
            name="interactive_selector",
            field=models.CharField(
                blank=True,
                default="",
                max_length=128,
                verbose_name="Interactive selector",
                help_text="Optional interactive verification area, e.g. css=#mfa-dialog. Exclude credentials and password visibility controls.",
            ),
        ),
    ]
