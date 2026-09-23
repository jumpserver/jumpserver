from django.dispatch import Signal

# Synchronous domain effects participate in the engine transaction. Receivers
# must schedule external delivery with transaction.on_commit.
workflow_event = Signal()
