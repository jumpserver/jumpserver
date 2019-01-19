#!/usr/bin/env python

import requests
import sys

admin_username = 'admin'
admin_password = 'admin'
domain_url = 'http://localhost:8080'


class UserCreation:
    headers = {}

    def __init__(self, username, password, domain):
        self.username = username
        self.password = password
        self.domain = domain

    def auth(self):
        url = "{}/api/users/v1/auth/".format(self.domain)
        data = {"username": self.username, "password": self.password}
        resp = requests.post(url, data=data)
        if resp.status_code == 200:
            data = resp.json()
            self.headers.update({
                'Authorization': '{} {}'.format('Bearer', data['token'])
            })
        else:
            print("用户名 或 密码 或 地址 不对")
            sys.exit(2)

    def get_user_detail(self, name, url):
        resp = requests.get(url, headers=self.headers)
        if resp.status_code == 200:
            data = resp.json()
            if len(data) < 1:
                return None
            for d in data:
                if d['name'] == name:
                    return d
            return None
        return None

    def get_system_user_detail(self, name):
        url = '{}/api/assets/v1/system-user/?name={}'.format(self.domain, name)
        return self.get_user_detail(name, url)

    def create_system_user(self, info):
        system_user = self.get_system_user_detail(info.get('name'))
        if system_user:
            return system_user
        url = '{}/api/assets/v1/system-user/'.format(self.domain)
        resp = requests.post(url, data=info, headers=self.headers, json=False)
        if resp.status_code == 201:
            return resp.json()
        else:
            print("创建系统用户失败: {} {}".format(info['name'], resp.content))
            return None

    def set_system_user_auth(self, system_user, info):
        url = '{}/api/assets/v1/system-user/{}/auth-info/'.format(
            self.domain, system_user['id']
        )
        data = {'password': info.get('password')}
        resp = requests.patch(url, data=data, headers=self.headers)
        if resp.status_code > 300:
            print("设置系统用户密码失败: {} {}".format(
                system_user.get('name'), resp.content.decode()
            ))
        else:
            return True

    def get_admin_user_detail(self, name):
        url = '{}/api/assets/v1/admin-user/?name={}'.format(self.domain, name)
        return self.get_user_detail(name, url)

    def create_admin_user(self, info):
        admin_user = self.get_admin_user_detail(info.get('name'))
        if admin_user:
            return admin_user
        url = '{}/api/assets/v1/admin-user/'.format(self.domain)
        resp = requests.post(url, data=info, headers=self.headers, json=False)
        if resp.status_code == 201:
            return resp.json()
        else:
            print("创建管理用户失败: {} {}".format(info['name'], resp.content.decode()))
            return None

    def set_admin_user_auth(self, admin_user, info):
        url = '{}/api/assets/v1/admin-user/{}/auth/'.format(
            self.domain, admin_user['id']
        )
        data = {'password': info.get('password')}
        resp = requests.patch(url, data=data, headers=self.headers)
        if resp.status_code > 300:
            print("设置管理用户密码失败: {} {}".format(
                admin_user.get('name'), resp.content.decode()
            ))
        else:
            return True

    def create_system_users(self):
        print("#"*10, " 开始创建系统用户 ", "#"*10)
        users = []
        f = open('system_users.txt')
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            name, username, password, protocol, auto_push = line.split()[:5]
            info = {
                "name": name,
                "username": username,
                "password": password,
                "protocol": protocol,
                "auto_push": bool(int(auto_push)),
                "login_mode": "auto"
            }
            users.append(info)

        for i, info in enumerate(users, start=1):
            system_user = self.create_system_user(info)
            if system_user and self.set_system_user_auth(system_user, info):
                print("[{}] 创建系统用户成功: {}".format(i, system_user['name']))

    def create_admin_users(self):
        print("\n", "#"*10, " 开始创建管理用户 ", "#"*10)
        users = []
        f = open('admin_users.txt')
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            name, username, password = line.split()[:3]
            info = {
                "name": name,
                "username": username,
                "password": password,
            }
            users.append(info)
        for i, info in enumerate(users, start=1):
            admin_user = self.create_admin_user(info)
            if admin_user and self.set_admin_user_auth(admin_user, info):
                print("[{}] 创建管理用户成功: {}".format(i, admin_user['name']))


def main():
    api = UserCreation(username=admin_username,
                       password=admin_password,
                       domain=domain_url)
    api.auth()
    api.create_system_users()
    api.create_admin_users()


if __name__ == '__main__':
    main()


