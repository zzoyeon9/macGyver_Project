# macGyver
Django Web(Only Create / Read / Update / Delete function with no Design & Front) & Infra deployment project 



## Architecture

![스크린샷 2022-08-18 오전 10 15 35](https://user-images.githubusercontent.com/47707808/185270820-fca3f02a-ca91-4fa8-ad02-7b3deac4dac0.png)

A simple CRUD web developed by Django is placed on servers B and C on the Nginx web server.
(These servers are simply installed only Centos7.)

Redis was used for caching, PostgrSQL for general DB use.

Finally, load-balancing is performed using a round-robin method through a Haproxy.

## Function

1. Team Member List Lookup
  - you can look up Team member list. 
2. Add a member
  - you can add a member to the team.
3. Change member information
  - you can update the member info.
4. Deleting a member
  - you can delete a memeber
5. Caching 
  - Data imported from DB is temporarily stored in Cache (Redis), and if the data is rewritten, the data is immediately retrieved and used through Redis without access to DB.
6. Load Balancing
  - Even if it is accessed through the same address through a load balancer called Haproxy on server A, traffic is evenly distributed to server B and server C through round-robin scheduling.


![스크린샷 2022-08-18 오후 3 24 54](https://user-images.githubusercontent.com/47707808/185309511-5a96595e-b07f-47e9-93f8-5e5686150eb0.png)

![image](https://user-images.githubusercontent.com/47707808/185310218-bf89706a-b5cc-4c26-87bc-d58c2238f9be.png)


## Technologies Used

- Django, HAproxy, Nginx, postgreSQL, Redis, Docker, Linux(Centos 7), Shell script, Python, uwsgi

## Duration
3 Months

## Member
Me
