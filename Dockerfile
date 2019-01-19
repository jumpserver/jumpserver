FROM registry.fit2cloud.com/public/python:v3
MAINTAINER Jumpserver Team <ibuler@qq.com>

WORKDIR /opt/jumpserver
RUN useradd jumpserver

COPY ./requirements /tmp/requirements

RUN yum -y install epel-release openldap-clients telnet && cd /tmp/requirements && \
    yum -y install $(cat rpm_requirements.txt)

RUN cd /tmp/requirements &&  pip install -r requirements.txt

COPY . /opt/jumpserver
RUN echo > config.yml
VOLUME /opt/jumpserver/data
VOLUME /opt/jumpserver/logs

ENV LANG=zh_CN.UTF-8
ENV LC_ALL=zh_CN.UTF-8

EXPOSE 8080
ENTRYPOINT ["./entrypoint.sh"]
