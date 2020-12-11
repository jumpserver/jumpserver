# 编译代码
FROM python:3.8.6-slim as stage-build
MAINTAINER JumpServer Team <ibuler@qq.com>
ARG VERSION
ENV VERSION=$VERSION

WORKDIR /opt/jumpserver
ADD . .
RUN cd utils && bash -ixeu build.sh


# 构建运行时环境
FROM python:3.8.6-slim
ARG PIP_MIRROR=https://pypi.douban.com/simple
ENV PIP_MIRROR=$PIP_MIRROR
ARG PIP_JMS_MIRROR=https://pypi.douban.com/simple
ENV PIP_JMS_MIRROR=$PIP_JMS_MIRROR

WORKDIR /opt/jumpserver

COPY ./requirements/deb_buster_requirements.txt ./requirements/deb_buster_requirements.txt
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list \
    && sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list \
    && apt update \
    && grep -v '^#' ./requirements/deb_buster_requirements.txt | xargs apt -y install \
    && localedef -c -f UTF-8 -i zh_CN zh_CN.UTF-8 \
    && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

COPY ./requirements/requirements.txt ./requirements/requirements.txt
RUN pip install --upgrade pip==20.2.4 setuptools==49.6.0 wheel==0.34.2 -i ${PIP_MIRROR} \
    && pip config set global.index-url ${PIP_MIRROR} \
    && pip install --no-cache-dir $(grep 'jms' requirements/requirements.txt) -i ${PIP_JMS_MIRROR} \
    && pip install --no-cache-dir -r requirements/requirements.txt

COPY --from=stage-build /opt/jumpserver/release/jumpserver /opt/jumpserver
RUN mkdir -p /root/.ssh/ \
    && echo "Host *\n\tStrictHostKeyChecking no\n\tUserKnownHostsFile /dev/null" > /root/.ssh/config

RUN echo > config.yml
VOLUME /opt/jumpserver/data
VOLUME /opt/jumpserver/logs

ENV LANG=zh_CN.UTF-8

EXPOSE 8070
EXPOSE 8080
ENTRYPOINT ["./entrypoint.sh"]
