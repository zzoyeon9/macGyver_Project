
# Centos7 세팅
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

USER irteam

WORKDIR /home1/irteam/
RUN mkdir apps

WORKDIR /home1/irteam/apps
##############

# Nginx Install
RUN wget http://nginx.org/download/nginx-1.16.1.tar.gz && tar -xvzf nginx-1.16.1.tar.gz

WORKDIR nginx-1.16.1

RUN ./configure --prefix=/home1/irteam/apps/nginx --with-http_ssl_module --with-http_stub_status_module && make && make install

WORKDIR /home1/irteam/apps/nginx/
# config Files, Certification
COPY nginx.conf /home1/irteam/apps/nginx/conf/
COPY webB_nginx.conf /home1/irteam/apps/nginx/conf/
COPY ssl /home1/irteam/apps/nginx/ssl
# Well-known Port
USER root

RUN chown -R irteam:irteam /home1/irteam/apps/nginx && chown root:irteam /home1/irteam/apps/nginx/sbin/nginx && chmod 4755 /home1/irteam/apps/nginx/sbin/nginx

USER irteam
WORKDIR /home1/irteam/apps/

## Python Install
RUN wget https://www.python.org/ftp/python/3.6.10/Python-3.6.10.tgz && \
tar -xvzf Python-3.6.10.tgz

WORKDIR /home1/irteam/apps/Python-3.6.10

RUN ./configure --prefix=/home1/irteam/apps/python3 && \
make && make install

WORKDIR /home1/irteam/apps/python3/bin/

## Django install
RUN ./pip3 install Django==2.2.10

RUN mkdir /home1/irteam/apps/web/
RUN ./django-admin startproject webB /home1/irteam/apps/web
COPY web /home1/irteam/apps/web

USER root
RUN chown -R irteam:irteam /home1/irteam/apps/web
RUN yum -y install python-setuptools
RUN easy_install pip && \
yum -y install python-devel

USER irteam
RUN ./pip3 install psycopg2-binary
RUN pip install django-redis
RUN ./pip3 install django-redis && ./pip3 install uwsgi
## Nginx Execution
WORKDIR /home1/irteam/apps/nginx/sbin
RUN ./nginx -c conf/nginx.conf
WORKDIR /home1/irteam/apps
RUN mkdir sock
WORKDIR /home1/irteam/apps/web/
CMD ["/home1/irteam/apps/python3/bin/uwsgi", "--socket", "/home1/irteam/apps/sock/webB.sock", "--module", "webB.wsgi"]

