from django.db import connections
from django.test.runner import DiscoverRunner


class WorkflowTestRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        # The runtime SQLite alias is added after Django configures DATABASES,
        # so it does not receive Django's usual TEST defaults.
        for alias in connections:
            connections[alias].settings_dict.setdefault('TEST', {'MIRROR': None})
        # Startup model discovery may have opened the isolated PostgreSQL DB.
        # Release it before Django attempts to recreate that test database.
        connections.close_all()
        return super().setup_databases(**kwargs)
