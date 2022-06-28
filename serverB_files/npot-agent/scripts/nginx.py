#!/home1/irteam/python3/bin/python3
import requests
import datetime
URL = 'http://10.113.99.60/stats'

#params = {'active_connections' : 'value1', 'handled_requests' : 'value2', 'reading' : 'value3', 'writing', : 'value4', 'waiting' : 'value5'}

def get_URL():
    response = requests.get(URL)
    return response

def print_webData(response):
    print(response.text)

def get_timeStamp():

    current_time = datetime.datetime.now()
    timeStamp = current_time.timestamp()
    return timeStamp


def get_parsing(response):

    datas = {}
    datas[str(response.text).split("\n")[1].split(" ")[1]] = str(response.text).split("\n")[2].split(" ")[1]
    datas[str(response.text).split("\n")[1].split(" ")[2]] = str(response.text).split("\n")[2].split(" ")[2]
    datas[str(response.text).split("\n")[1].split(" ")[3]] = str(response.text).split("\n")[2].split(" ")[3]
    return datas


response = get_URL()
datas = get_parsing(response)
TIMESTAMP = get_timeStamp()

print("nginx.accepts","%d" % TIMESTAMP, datas["accepts"], "cluster=zzoyeon9","host=10.113.99.60")
print("nginx.handled","%d" % TIMESTAMP, datas["handled"], "cluster=zzoyeon9","host=10.113.99.60")
print("nginx.requests","%d" % TIMESTAMP, datas["requests"], "cluster=zzoyeon9","host=10.113.99.60")

