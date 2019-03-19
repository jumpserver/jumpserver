# -*- coding: utf-8 -*-
#
import os

import ipdb

ipip_db = None


def get_ip_city(ip):
    global ipip_db
    if ipip_db is None:
        ipip_db_path = os.path.join(os.path.dirname(__file__), 'ipipfree.ipdb')
        ipip_db = ipdb.City(ipip_db_path)
    info = list(set(ipip_db.find(ip, 'CN')))
    if '' in info:
        info.remove('')
    return ' '.join(info)