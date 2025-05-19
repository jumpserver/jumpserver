# -*- coding: utf-8 -*-
#
import os

import ipdb

__all__ = ['get_ip_city_by_ipip']
ipip_db = None


def get_ip_city_by_ipip(ip):
    global ipip_db
    if ipip_db is None:
        ipip_db_path = os.path.join(os.path.dirname(__file__), 'ipipfree.ipdb')
        if not os.path.exists(ipip_db_path):
            raise FileNotFoundError(
                f"IP database not found, please run `bash ./requirements/static_files.sh`")
        ipip_db = ipdb.City(ipip_db_path)
    try:
        info = ipip_db.find_info(ip, 'CN')
    except ValueError:
        return None
    if not info:
        raise None
    return {'city': info.city_name, 'country': info.country_name}
