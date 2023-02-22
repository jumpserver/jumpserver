from common.utils import get_logger

logger = get_logger(__name__)

#
# @receiver(pre_save, sender=Account)
# def on_account_pre_save(sender, instance, **kwargs):
#     if instance.secret != instance.pre_secret:
#         instance.pre_secret = instance.secret
#
#
# @receiver(post_save, sender=Account)
# @on_transaction_commit
# def on_account_post_create(sender, instance, created=False, **kwargs):
#     if created or instance.secret != instance.pre_secret:
#         Account.objects.filter(id=instance.id) \
#             .update(version=F('version') + 1)
