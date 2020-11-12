##centos7 세팅
FROM base.registry.navercorp.com/centos:centos7

LABEL MAINTAINER "CHO YEON JUN<yj.cho7@navercorp.com>"
USER root
RUN yum clean all && \
yum repolist && \
yum -y update && \
yum -y install gcc pcre-devel zlib-devel openssl-devel wget make gcc-c++ sudo
EXPOSE 80
EXPOSE 443
EXPOSE 8000
EXPOSE 8001
EXPOSE 6379
RUN yum -y install readline-devel.x86_64
USER irteam

WORKDIR /home1/irteam/
RUN mkdir apps

WORKDIR /home1/irteam/apps
##############
## redis Install

RUN wget http://download.redis.io/releases/redis-5.0.7.tar.gz
RUN tar -xvzf redis-5.0.7.tar.gz
WORKDIR /home1/irteam/apps/redis-5.0.7
RUN make
RUN make install PREFIX=/home1/irteam/apps/redis

COPY redis/redis.conf /home1/irteam/apps/redis/

USER root
RUN chown irteam:irteam /home1/irteam/apps/redis/redis.conf
USER irteam

WORKDIR /home1/irteam/apps/redis/bin
CMD ["./redis-server", "/home1/irteam/apps/redis/redis.conf"]
