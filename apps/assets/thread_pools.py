"""
做异步的话，每个APP启动了多少线程池应该很容易被查找，所以把线程池的初始化集中
在这个模块中
"""
from concurrent.futures import ThreadPoolExecutor


class UpdateNodeAssetsAmountThreadPool(ThreadPoolExecutor):
    """
    单例
    """
    _object = None

    def __new__(cls):
        if cls._object is None:
            cls._object = ThreadPoolExecutor(
                max_workers=5,
                thread_name_prefix='update_node_asset_amount'
            )
        return cls._object
