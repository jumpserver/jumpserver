from concurrent.futures import ThreadPoolExecutor


class SingletonThreadPoolExecutor(ThreadPoolExecutor):
    """
    该类不要直接实例化
    """

    def __new__(cls, max_workers=None, thread_name_prefix=None):
        if cls is SingletonThreadPoolExecutor:
            raise NotImplementedError
        if getattr(cls, '_object', None) is None:
            cls._object = ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix=thread_name_prefix
            )
        return cls._object
