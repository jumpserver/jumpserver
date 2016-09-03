#!/usr/bin/env python
import os
import sys
import errno

if __name__ == "__main__":
    try:
        os.makedirs('./logs')
    except OSError as exc: # Python > 2.5 (except OSError, exec: for Python < 2.5)
        if exc.errno == errno.EEXIST and os.path.isdir('./logs'):
            pass
        else: raise

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jumpserver.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing to avoid masking other
        # exceptions on Python 2.
        try:
            import django
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
        raise
    execute_from_command_line(sys.argv)
