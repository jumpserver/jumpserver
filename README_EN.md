## Jumpserver 

[![Python3](https://img.shields.io/badge/python-3.6-green.svg?style=plastic)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-2.2-brightgreen.svg?style=plastic)](https://www.djangoproject.com/)
[![Docker Pulls](https://img.shields.io/docker/pulls/jumpserver/jms_all.svg)](https://hub.docker.com/u/jumpserver)

---- 
## CRITICAL BUG WARNING

JumpServer found a critical bug for pre auth and info leak, You should fix quickly.

Thanks for reactivity of Alibaba Hackerone bug bounty program report us this bug

**Vulnerable version:**
```
< v2.6.2
< v2.5.4
< v2.4.5 
= v1.5.9
```

**Safe version:**
```
>= v2.6.2
>= v2.5.4
>= v2.4.5 
= v1.5.9 （Unstander version, so no change）
```

**Fix method:**
Upgrade to save version


**Quick temporary fix method:(recommend)**

Modify nginx config file, disable vulnerable api

```
/api/v1/authentication/connection-token/
/api/v1/users/connection-token/
```

Nginx config path

```
# Community old version
/etc/nginx/conf.d/jumpserver.conf

# Enterpise old version
jumpserver-release/nginx/http_server.conf
 
# New version
jumpserver-release/compose/config_static/http_server.conf
```

Modify nginx config 

```
### On the server location top, or before of /api and /
location /api/v1/authentication/connection-token/ {
   return 403;
}
 
location /api/v1/users/connection-token/ {
   return 403;
}
### Add two location above
 
location /api/ {
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_pass http://core:8080;
  }
 
...
```

Then restart nginx

```
docker deployment: 
$ docker restart jms_nginx

rpm or other deployment:
$ systemctl restart nginx

```

**Fix verify**

```
$ wget https://github.com/jumpserver/jumpserver/releases/download/v2.6.2/jms_bug_check.sh 

# bash jms_bug_check.sh HOST 
$ bash jms_bug_check.sh demo.jumpserver.org
漏洞已修复 (fixed)
漏洞未修复 (vulnerable)
```


**Attack detection**

Download the check script under the directory logs than the gunicorn on 

```
$ pwd
/opt/jumpserver/core/logs

$ ls gunicorn.log
gunicorn.log

$ wget 'https://github.com/jumpserver/jumpserver/releases/download/v2.6.2/jms_check_attack.sh'
$ bash jms_check_attack.sh
系统未被入侵 (safe)
系统已被入侵 (attacked)
```

--------------------------

----

- [中文版](https://github.com/jumpserver/jumpserver/blob/master/README.md)

Jumpserver is the first fully open source bastion in the world, based on the GNU GPL v2.0 open source protocol. Jumpserver is a  professional operation and maintenance audit system conforms to 4A specifications.

Jumpserver is developed using Python / Django, conforms to the Web 2.0 specification, and is equipped with the industry-leading Web Terminal solution which have beautiful interface and great user experience.

Jumpserver adopts a distributed architecture to support multi-branch deployment across multiple areas. The central node provides APIs, and login nodes are deployed in each branch. It can be scaled horizontally without concurrency restrictions.

Change the world, starting from little things.

----

### Features

 ![Jumpserver 功能](https://jumpserver-release.oss-cn-hangzhou.aliyuncs.com/Jumpserver148.jpeg "Jumpserver 功能")

### Start 

Quick start  [Docker Install](http://docs.jumpserver.org/zh/docs/dockerinstall.html)

Step by Step deployment. [Docs](http://docs.jumpserver.org/zh/docs/step_by_step.html)

Full documentation [Docs](http://docs.jumpserver.org)

### Demo、Video 和 Snapshot

We provide online demo, demo video and screenshots to get you started quickly.

[Demo](https://demo.jumpserver.org/auth/login/?next=/)
[Video](https://fit2cloud2-offline-installer.oss-cn-beijing.aliyuncs.com/tools/Jumpserver%20%E4%BB%8B%E7%BB%8Dv1.4.mp4)
[Snapshot](http://docs.jumpserver.org/zh/docs/snapshot.html)

### SDK

We provide the SDK for your other systems to quickly interact with the Jumpserver API.

- [Python](https://github.com/jumpserver/jumpserver-python-sdk) Jumpserver other components use this SDK to complete the interaction.
- [Java](https://github.com/KaiJunYan/jumpserver-java-sdk.git) 恺珺同学提供的Java版本的SDK thanks to 恺珺 for provide Java SDK


### License & Copyright
Copyright (c) 2014-2019 Beijing Duizhan Tech, Inc., All rights reserved.

Licensed under The GNU General Public License version 2 (GPLv2)  (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

https://www.gnu.org/licenses/gpl-2.0.html

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
