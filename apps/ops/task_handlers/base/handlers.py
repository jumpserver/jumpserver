"""
执行改密计划的基类
"""
from common.utils import get_logger

logger = get_logger(__file__)


class BaseHandler:
    def __init__(self, task, show_step_info=True):
        self.task = task
        self.conn = None
        self.retry_times = 3
        self.current_step = 0
        self.is_frozen = False  # 任务状态冻结标志
        self.show_step_info = show_step_info
