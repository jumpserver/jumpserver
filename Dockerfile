FROM registry.fit2cloud.com/public/python:v3 as stage-build
MAINTAINER Jumpserver Team <ibuler@qq.com>
ARG VERSION
ENV VERSION=$VERSION

WORKDIR /opt/jumpserver
ADD . .
RUN cd utils && bash -ixeu build.sh


FROM registry.fit2cloud.com/public/python:v3
ARG PIP_MIRROR=https://pypi.douban.com/simple
ENV PIP_MIRROR=$PIP_MIRROR
ARG PIP_JMS_MIRROR=https://pypi.douban.com/simple
ENV PIP_JMS_MIRROR=$PIP_JMS_MIRROR
ARG MYSQL_MIRROR=https://mirrors.tuna.tsinghua.edu.cn/mysql/yum/mysql57-community-el6/
ENV MYSQL_MIRROR=$MYSQL_MIRROR

WORKDIR /opt/jumpserver

COPY ./requirements ./requirements
RUN useradd jumpserver
RUN wget -O /etc/yum.repos.d/CentOS-Base.repo http://mirrors.aliyun.com/repo/Centos-6.repo
RUN yum -y install epel-release && \
      echo -e "[mysql]\nname=mysql\nbaseurl=${MYSQL_MIRROR}\ngpgcheck=0\nenabled=1" > /etc/yum.repos.d/mysql.repo
RUN yum -y install $(cat requirements/rpm_requirements.txt)
RUN pip install --upgrade pip==20.2.4 setuptools==49.6.0 wheel==0.34.2 -i ${PIP_MIRROR} && \
    pip config set global.index-url ${PIP_MIRROR}
RUN pip install --no-cache-dir $(grep 'jms' requirements/requirements.txt) -i ${PIP_JMS_MIRROR}
RUN pip install --no-cache-dir -r requirements/requirements.txt

COPY --from=stage-build /opt/jumpserver/release/jumpserver /opt/jumpserver
RUN mkdir -p /root/.ssh/ && echo -e "Host *\n\tStrictHostKeyChecking no\n\tUserKnownHostsFile /dev/null" > /root/.ssh/config

RUN echo > config.yml
VOLUME /opt/jumpserver/data
VOLUME /opt/jumpserver/logs

ENV LANG=zh_CN.UTF-8
ENV LC_ALL=zh_CN.UTF-8

EXPOSE 8070
EXPOSE 8080
ENTRYPOINT ["./entrypoint.sh"]
