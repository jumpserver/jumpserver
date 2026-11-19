import threading


class SubscriptionWebsocketMixin:
    """Keep subscription cleanup tied to the consumer's ASGI lifetime."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sub = None
        self._subscription_lock = threading.Lock()
        self._subscription_closed = False

    async def __call__(self, *args, **kwargs):
        try:
            return await super().__call__(*args, **kwargs)
        finally:
            self.close_subscription()

    def register_subscription(self, subscription):
        # Cancellation can finish __call__ while a sync connect handler is still
        # creating its subscription in another thread.
        with self._subscription_lock:
            if self._subscription_closed:
                previous = subscription
            else:
                previous, self.sub = self.sub, subscription
        if previous is not None:
            previous.unsubscribe()

    def close_subscription(self):
        with self._subscription_lock:
            self._subscription_closed = True
            subscription, self.sub = self.sub, None
        if subscription is not None:
            subscription.unsubscribe()

    def disconnect(self, code):
        self.close_subscription()
        return super().disconnect(code)
