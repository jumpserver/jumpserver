FROM registry.fit2cloud.com/public/python:v3
MAINTAINER Jumpserver Team <ibuler@qq.com>

ENV LANG=en_US.UTF-8

WORKDIR /opt/jumpserver
RUN useradd jumpserver

COPY ./requirements /tmp/requirements

RUN wget -O /etc/yum.repos.d/CentOS-Base.repo http://mirrors.aliyun.com/repo/Centos-6.repo \
    && sed -i 's@/centos/@/centos-vault/@g' /etc/yum.repos.d/CentOS-Base.repo \
    && sed -i 's@$releasever@6.10@g' /etc/yum.repos.d/CentOS-Base.repo

RUN yum -y install epel-release && \
      echo -e "[mysql]\nname=mysql\nbaseurl=https://mirrors.tuna.tsinghua.edu.cn/mysql/yum/mysql57-community-el6/\ngpgcheck=0\nenabled=1" > /etc/yum.repos.d/mysql.repo
RUN cd /tmp/requirements && yum -y install $(cat rpm_requirements.txt)
RUN cd /tmp/requirements && pip install --upgrade pip setuptools==49.6.0 && pip install wheel && \
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt || pip install -r requirements.txt
RUN mkdir -p /root/.ssh/ && echo -e "Host *\n\tStrictHostKeyChecking no\n\tUserKnownHostsFile /dev/null" > /root/.ssh/config

COPY . /opt/jumpserver
RUN echo > config.yml
VOLUME /opt/jumpserver/data
VOLUME /opt/jumpserver/logs

EXPOSE 8070
EXPOSE 8080
ENTRYPOINT ["./entrypoint.sh"]
