# -*- coding: utf-8 -*-
#
import socket
import struct
import random


def random_datetime(date_start, date_end):
    random_delta = (date_end - date_start) * random.random()
    return date_start + random_delta


def random_ip():
    return socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff)))



# def strTimeProp(start, end, prop, fmt):
#     time_start = time.mktime(time.strptime(start, fmt))
#     time_end = time.mktime(time.strptime(end, fmt))
#     ptime = time_start + prop * (time_end - time_start)
#     return int(ptime)
#
#
# def randomTimestamp(start, end, fmt='%Y-%m-%d %H:%M:%S'):
#     return strTimeProp(start, end, random.random(), fmt)
#
#
# def randomDate(start, end, frmt='%Y-%m-%d %H:%M:%S'):
#     return time.strftime(frmt, time.localtime(strTimeProp(start, end, random.random(), frmt)))
#
#
# def randomTimestampList(start, end, n, frmt='%Y-%m-%d %H:%M:%S'):
#     return [randomTimestamp(start, end, frmt) for _ in range(n)]
#
#
# def randomDateList(start, end, n, frmt='%Y-%m-%d %H:%M:%S'):
#     return [randomDate(start, end, frmt) for _ in range(n)]

