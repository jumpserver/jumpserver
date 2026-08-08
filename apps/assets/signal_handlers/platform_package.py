from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from assets.const import AllTypes
from assets.models import Platform, PlatformPackage


@receiver(post_delete, sender=Platform)
def delete_unused_platform_package(instance, **kwargs):
    package = instance.package
    if package is None or package.platforms.exists():
        return

    package.delete()


@receiver(post_delete, sender=PlatformPackage)
def delete_platform_package_files(instance, **kwargs):
    def cleanup():
        instance.delete_files()
        AllTypes.reload_automation_methods()

    transaction.on_commit(cleanup)
