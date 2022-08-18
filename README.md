# macGyver
Django Web & Infra deployment project



## Architecture

![스크린샷 2022-08-18 오전 10 15 35](https://user-images.githubusercontent.com/47707808/185270820-fca3f02a-ca91-4fa8-ad02-7b3deac4dac0.png)

A simple CRUD web developed by Django is placed on servers B and C on the Nginx web server.
(These servers are simply installed only Centos7.)

Redis was used for caching, PostgrSQL for general DB use.

Finally, load-balancing is performed using a round-robin method through a Haproxy.

## Technologies Used

- Django, HAproxy, Nginx, postgreSQL, Redis, Docker, Linux(Centos 7), Shell script, Python, uwsgi

## Duration
3 Months

## Member
Me
