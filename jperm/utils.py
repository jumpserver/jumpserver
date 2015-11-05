# -*- coding: utf-8 -*-

import random

def get_rand_pass():
    """
    get a reandom password.
    """
    lower = [chr(i) for i in range(97,123)]
    upper = [chr(i).upper() for i in range(97,123)]
    digit = [str(i) for i in range(10)]
    password_pool = []
    password_pool.extend(lower)
    password_pool.extend(upper)
    password_pool.extend(digit)
    pass_list = [random.choice(password_pool) for i in range(1,14)]
    pass_list.insert(random.choice(range(1,14)), '@')
    pass_list.insert(random.choice(range(1,14)), random.choice(digit))
    password = ''.join(pass_list)
    return password

def updates_dict(*args):
    """
    surport update multi dict
    """
    result = {}
    for d in args:
        result.update(d)
    return result



if __name__ == "__main__":
    pass


