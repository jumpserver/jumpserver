# -*- coding: utf-8 -*-
#
import time
from openpyxl import Workbook
from django.utils import timezone

from common.utils import get_logger
from common.utils.timezone import local_now_display

logger = get_logger(__file__)


class BaseExecutionManager:
    task_back_up_serializer: None

    def __init__(self, execution):
        self.execution = execution
        self.date_start = timezone.now()
        self.time_start = time.time()
        self.date_end = None
        self.time_end = None
        self.timedelta = 0
        self.total_tasks = []

    def on_tasks_pre_run(self, tasks):
        raise NotImplementedError

    def on_per_task_pre_run(self, task, total, index):
        raise NotImplementedError

    def create_csv_file(self, tasks, file_name):
        raise NotImplementedError

    def get_handler_cls(self):
        raise NotImplemented

    def do_run(self):
        tasks = self.total_tasks = self.execution.create_plan_tasks()
        self.on_tasks_pre_run(tasks)
        total = len(tasks)

        for index, task in enumerate(tasks, start=1):
            self.on_per_task_pre_run(task, total, index)
            task.start(show_step_info=False)

    def pre_run(self):
        self.execution.date_start = self.date_start
        self.execution.save()
        self.show_execution_steps()

    def show_execution_steps(self):
        pass

    def show_summary(self):
        split_line = '#' * 40
        summary = self.execution.result_summary
        logger.info(f'\n{split_line} 改密计划执行结果汇总 {split_line}')
        logger.info(
            '\n成功: {succeed}, 失败: {failed}, 总数: {total}\n'
            ''.format(**summary)
        )

    def post_run(self):
        self.time_end = time.time()
        self.date_end = timezone.now()

        logger.info('\n\n' + '-' * 80)
        logger.info('任务执行结束 {}\n'.format(local_now_display()))
        self.timedelta = int(self.time_end - self.time_start)
        logger.info('用时: {}s'.format(self.timedelta))
        self.execution.timedelta = self.timedelta
        self.execution.save()
        self.show_summary()

    def run(self):
        self.pre_run()
        self.do_run()
        self.post_run()
