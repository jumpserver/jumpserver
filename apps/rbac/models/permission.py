from django.contrib.auth.models import Permission as DjangoPermission


class Permission(DjangoPermission):

    class Meta:
        proxy = True
