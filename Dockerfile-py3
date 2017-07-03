FROM centos:centos6
LABEL MAINTAINER Jumpserver Team <ibuler@qq.com>

WORKDIR /tmp

RUN yum -y install wget sqlite-devel xz gcc automake zlib-devel openssl-devel; yum clean all

# Install Python
RUN wget https://www.python.org/ftp/python/3.6.1/Python-3.6.1.tar.xz && \
    tar xvf Python-3.6.1.tar.xz  && cd Python-3.6.1 && ./configure && make && make install &&  \
    rm -rf /tmp/{Python-3.6.1.tar.xz,Python-3.6.1}

RUN mv /usr/bin/python /usr/bin/python2
RUN ln -s /usr/local/bin/python3 /usr/bin/python && ln -s /usr/local/bin/pip3 /usr/bin/pip
RUN sed -i 's@/usr/bin/python@/usr/bin/python2@g' /usr/bin/yum

