FROM registry.fit2cloud.com/public/python:v3 as stage-build
MAINTAINER Jumpserver Team <ibuler@qq.com>
ARG VERSION
ENV VERSION=$VERSION

WORKDIR /opt/jumpserver
ADD . .
RUN cd utils && bash -ixeu build.sh


FROM registry.fit2cloud.com/public/python:v3
WORKDIR /opt/jumpserver
COPY --from=stage-build /opt/jumpserver/release/jumpserver /opt/jumpserver

RUN useradd jumpserver

RUN yum -y install epel-release && \
      echo -e "[mysql]\nname=mysql\nbaseurl=https://mirrors.tuna.tsinghua.edu.cn/mysql/yum/mysql57-community-el6/\ngpgcheck=0\nenabled=1" > /etc/yum.repos.d/mysql.repo

COPY . .
RUN yum -y install $(cat requirements/rpm_requirements.txt)
RUN pip install --upgrade pip setuptools && pip install wheel && \
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements/requirements.txt || pip install -r requirements/requirements.txt
RUN mkdir -p /root/.ssh/ && echo -e "Host *\n\tStrictHostKeyChecking no\n\tUserKnownHostsFile /dev/null" > /root/.ssh/config

RUN echo > config.yml
VOLUME /opt/jumpserver/data
VOLUME /opt/jumpserver/logs

ENV LANG=zh_CN.UTF-8
ENV LC_ALL=zh_CN.UTF-8

EXPOSE 8070
EXPOSE 8080
ENTRYPOINT ["./entrypoint.sh"]
