# -*- coding: utf-8 -*-
#
from itertools import chain
from .utils import lazyproperty


class Stack(list):
    def is_empty(self):
        return len(self) == 0

    @property
    def top(self):
        if self.is_empty():
            return None
        return self[-1]

    @property
    def bottom(self):
        if self.is_empty():
            return None
        return self[0]

    def size(self):
        return len(self)

    def push(self, item):
        self.append(item)


class QuerySetChain:
    def __init__(self, querysets):
        self.querysets = querysets

    @lazyproperty
    def querysets_counts(self):
        counts = [s.count() for s in self.querysets]
        return counts

    def count(self):
        return self.total_count

    @lazyproperty
    def total_count(self):
        return sum(self.querysets_counts)

    def __iter__(self):
        self._chain = chain(*self.querysets)
        return self

    def __next__(self):
        return next(self._chain)

    def __getitem__(self, ndx):
        querysets_count_zip = zip(self.querysets, self.querysets_counts)
        length = 0   # 加上本数组后的大数组长度
        pre_length = 0  # 不包含本数组的大数组长度
        items = []  # 返回的值
        loop = 0

        if isinstance(ndx, slice):
            ndx_start = ndx.start or 0
            ndx_stop = ndx.stop or self.total_count
            ndx_step = ndx.step or 1
        else:
            ndx_start = ndx
            ndx_stop, ndx_step = None, None

        for queryset, count in querysets_count_zip:
            length += count
            loop += 1
            # 取当前数组的start角标, 存在3中情况
            # 1. start角标在当前数组
            if length > ndx_start >= pre_length:
                start = ndx_start - pre_length
                # print("[loop {}] Start is: {}".format(loop, start))
                if ndx_step is None:
                    return queryset[start]
            # 2. 不包含当前数组，因为起始已经超过了当前数组的长度
            elif ndx_start >= length:
                pre_length += count
                continue
            # 3. 不在当前数组，但是应该从当前数组0开始计算
            else:
                start = 0

            # 可能取单个值, ndx_stop 为None, 不应该再找
            if ndx_stop is None:
                pre_length += count
                continue

            # 取当前数组的stop角标, 存在2中情况
            # 不存在第3中情况是因为找到了会提交结束循环
            # 1. 结束角标小于length代表 结束位在当前数组上
            if ndx_stop < length:
                stop = ndx_stop - pre_length
            # 2. 结束位置包含改数组到了最后
            else:
                stop = count
            # print("[loop {}] Slice: {} {} {}".format(loop, start, stop, ndx_step))
            items.extend(list(queryset[slice(start, stop, ndx_step)]))
            pre_length += count

            # 如果结束再当前数组，则结束循环
            if ndx_stop < length:
                break
        return items
