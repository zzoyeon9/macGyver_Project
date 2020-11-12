# centos7 세팅
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
EXPOSE 5432

RUN yum -y install readline-devel.x86_64
USER irteam

WORKDIR /home1/irteam/
RUN mkdir apps

WORKDIR /home1/irteam/apps
##############

#Postgresql Install
RUN wget https://ftp.postgresql.org/pub/source/v12.1/postgresql-12.1.tar.gz && tar -xvzf postgresql-12.1.tar.gz
WORKDIR postgresql-12.1


RUN ./configure --prefix=/home1/irteam/apps/pgsql && make && make install

COPY data /home1/irteam/apps/pgsql/data/
USER root
RUN chown -R irteam:irteam /home1/irteam/apps/pgsql/data && chmod -R 750 /home1/irteam/apps/pgsql/data
USER irteam
WORKDIR /home1/irteam/apps/pgsql/bin/
CMD ["./postgres", "-D", "/home1/irteam/apps/pgsql/data"]

