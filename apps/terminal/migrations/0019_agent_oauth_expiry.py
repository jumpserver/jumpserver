from django.db import migrations, models

import terminal.models.agent


class Migration(migrations.Migration):
    dependencies = [('terminal', '0018_agent_mcp')]

    operations = [
        # The callable is evaluated once when adding the column, giving existing
        # authorizations seven days from this upgrade without reading them into RAM.
        migrations.AddField(
            model_name='agentoauthbinding',
            name='expires_at',
            field=models.DateTimeField(
                db_index=True, default=terminal.models.agent.agent_oauth_expiry,
            ),
        ),
    ]
