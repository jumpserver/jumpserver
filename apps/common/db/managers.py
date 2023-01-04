from django.db import models


class DebugQueryManager(models.Manager):
    def get_queryset(self):
        import traceback
        lines = traceback.format_stack()
        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        for line in lines[-10:-1]:
            print(line)
        print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        queryset = super().get_queryset()
        return queryset
