#!/usr/bin/env python
#
import re
import sqlite3
import sys


def is_weak_password(password):
    if len(password) < 8:
        return True

    # 判断是否只有一种字符类型
    if password.isdigit() or password.isalpha():
        return True

    # 判断是否只包含数字或字母
    if password.islower() or password.isupper():
        return True

    # 判断是否包含常见弱密码
    common_passwords = ["123456", "password", "12345678", "qwerty", "abc123"]
    if password.lower() in common_passwords:
        return True

    # 正则表达式判断字符多样性（数字、字母、特殊字符）
    if (
            not re.search(r"[A-Za-z]", password)
            or not re.search(r"[0-9]", password)
            or not re.search(r"[\W_]", password)
    ):
        return True
    return False


def parse_it(fname):
    count = 0
    lines = []
    with open(fname, 'rb') as f:
        for line in f:
            try:
                line = line.decode().strip()
            except UnicodeDecodeError:
                continue

            if len(line) > 32:
                continue

            if is_weak_password(line):
                continue

            lines.append(line)
            count += 0
            print(line)
    return lines


def insert_to_db(lines):
    conn = sqlite3.connect('./leak_passwords.db')
    cursor = conn.cursor()
    create_table_sql = '''
        CREATE TABLE IF NOT EXISTS passwords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            password CHAR(32)
        )
    '''
    create_index_sql = 'CREATE INDEX IF NOT EXISTS idx_password ON passwords(password)'
    cursor.execute(create_table_sql)
    cursor.execute(create_index_sql)

    for line in lines:
        cursor.execute('INSERT INTO passwords (password) VALUES (?)', [line])
    conn.commit()


if __name__ == '__main__':
    filename = sys.argv[1]
    lines = parse_it(filename)
    insert_to_db(lines)
