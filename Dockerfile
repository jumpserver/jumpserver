FROM registry.fit2cloud.com/public/python:v3
MAINTAINER Jumpserver Team <ibuler@qq.com>

WORKDIR /opt/jumpserver
RUN useradd jumpserver

COPY ./requirements /tmp/requirements

RUN yum -y install epel-release && rpm -ivh https://repo.mysql.com/mysql57-community-release-el6.rpm
RUN cd /tmp/requirements && yum -y install $(cat rpm_requirements.txt)
RUN cd /tmp/requirements && pip install --upgrade pip setuptools && \
    pip install -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt || pip install -r requirements.txt
RUN mkdir -p /root/.ssh/ && echo -e "Host *\n\tStrictHostKeyChecking no\n\tUserKnownHostsFile /dev/null" > /root/.ssh/config

COPY . /opt/jumpserver
RUN echo > config.yml
VOLUME /opt/jumpserver/data
VOLUME /opt/jumpserver/logs

ENV LANG=zh_CN.UTF-8
ENV LC_ALL=zh_CN.UTF-8

EXPOSE 8080
ENTRYPOINT ["./entrypoint.sh"]
