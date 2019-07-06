# -*- coding: utf-8 -*-
#


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
