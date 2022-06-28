#!/usr/bin/env python

import httplib
import sys
import time
import socket
import os
import pwd

try:
    import json
except ImportError:
    json = None

#######################################################################################################################
#
# Here is an example what you should define to make nbase.py scripts working:
#
# NBASE_METRIC_INTERVAL=15 : (Optional) It allow you to make sure to define an user custom interval to collect metrics.
#                                       The default is 15 seconds.
# NBASE_MGMT=1.2.3.4:15000 : (Required) You must define it with MGMT host ip and port.
# NBASE_CS=6220:16000,6320:16001,6420:16002,... : (Required) You must define it with csPort:csMonPort map using 
#                                                            a comma separator for multiple instances.
#
# NOTE: It only collects cs metrics in a local machine even though mgmt provides all cs ip list across multiple 
#       machines. Which means that you must install the script for all nbase-t machines.
#       However, mgmt metrics will be collected in only single machine where you define an ip as NBASE_MGMT env var.
#       Even though it uses loopback ip like `NBASE_MGMT=127.0.0.1:15000`, it will collect cs metrics but it won't be
#       collected mgmt metrics.
#######################################################################################################################

def drop_privileges(user="nobody"):
    """Drops privileges if running as root."""
    try:
        ent = pwd.getpwnam(user)
    except KeyError:
        return
    if os.getuid() != 0:
        return
    os.setgid(ent.pw_gid)
    os.setuid(ent.pw_uid)


def loadMonInterval():
    if 'NBASE_METRIC_INTERVAL' not in os.environ:
        return 15
    return int(os.environ['NBASE_METRIC_INTERVAL'])


def loadCsPortMap():
    nbaseCs = os.environ['NBASE_CS']
    if nbaseCs is None:
        return {}
    items = nbaseCs.split(',')
    ret = {}
    for item in items:
        ports = item.split(':')
        svcPort = int(ports[0])
        monPort = int(ports[1])
        ret[svcPort] = monPort
    return ret


def requestApi(client):
    client.request('GET', '/nbase_mon?item=all')
    resp = client.getresponse().read()
    return json.loads(resp)


def findCs(mgmtResponse, monPortMap, currentIp):
    ret = []
    if 'membership' in mgmtResponse:
        for membership in mgmtResponse['membership']:
            csPort = membership['port']
            if membership['ip'] == currentIp and csPort in monPortMap:
                membership['monPort'] = monPortMap[csPort]
                ret.append(membership)
    return ret


def printMgmtMetrics(mgmtResponse, timestamp):
    metrics = [
        'num_failed',
        'num_q0',
        'num_runq',
        'src_concurrency',
        'tgt_concurrency'
    ]
    if 'mig_sum' in mgmtResponse:
        migSum = mgmtResponse['mig_sum']
        for metric in metrics:
            if metric in migSum:
                printMgmtMetric('mig_sum.%s' % metric, timestamp, migSum[metric])


def printMgmtMetric(metric, timestamp, value):
    print 'nbase.mgmt.%s %d %s' % (metric, timestamp, value)


def printCsMetrics(jsonData, metricPrefix, timestamp, tags):
    if jsonData is not None:
        for key, value in jsonData.items():
            if key == 'timestamp':
                continue
            if isinstance(value, dict):
                printCsMetrics(value, '%s.%s' % (metricPrefix, key), timestamp, tags)
            elif isinstance(value, int) or isinstance(value, float):
                printCsMetric('%s.%s' % (metricPrefix, key), timestamp, value, tags)


def printCsMetric(metric, timestamp, value, tags):
    print '%s %d %s%s' % (metric, timestamp, value, tags)


def generateExtraTagStr(extra):
    tags = ''
    if extra is not None:
        for tagk, tagv in extra.items():
            tags = '%s %s=%s' % (tags, tagk, tagv)
    return tags


def printCsCompositeMetrics(jsonData, timestamp, tags):
    if jsonData is not None and 'connection' in jsonData:
        connection = jsonData['connection']
        if 'db_conn_in_pool' in connection and 'db_conn_in_used' in connection and 'db_conn_pool_size' in connection:
            value = int(connection['db_conn_in_used'] + connection['db_conn_in_pool']) * 100.0 / int(connection['db_conn_pool_size'])
            printCsMetric('nbase.cs.connection.pool_usage', timestamp, value, tags)
        if 'db_conn_borrow' in connection and 'db_conn_release' in connection:
            value = int(connection['db_conn_borrow']) - int(connection['db_conn_release'])
            printCsMetric('nbase.cs.connection.not_released', timestamp, value, tags)


def main():
    drop_privileges()
    if json is None:
        print >>sys.stderr, "error: Python module `json' is missing"
        return 13

    collectionInterval = loadMonInterval() # NBASE_METRIC_INTERVAL
    mgmtHost = os.environ['NBASE_MGMT']    # 1.2.3.4:15000
    monPortMap = loadCsPortMap()           # NBASE_CS=6220:16000,6320:16001,6420:16002,...
    currentIp = socket.gethostbyname(socket.gethostname())

    isMgmt = False
    if mgmtHost.split(':')[0] == currentIp:
        isMgmt = True

    mgmtClient = httplib.HTTPConnection(mgmtHost)
    csClients = {}

    while True:
        ts = int(time.time())

        mgmtResponse = requestApi(mgmtClient)
        if isMgmt:
            printMgmtMetrics(mgmtResponse, ts)

        
        memberships = findCs(mgmtResponse, monPortMap, currentIp)
        for membership in memberships:
            csHost = membership['ip']
            csPort = membership['port']
            csZone = membership['zone']
            csState = membership['state']
            csAccessMode = membership['db_access_mode']
            csMonPort = membership['monPort']

            extra = {
                'access_mode': csAccessMode,
                'port': csPort,
                'zone': csZone,
                'state': csState
            }

            if csHost and csPort and csMonPort:
                csClients[csPort] = httplib.HTTPConnection(csHost, csMonPort)

            if csPort in csClients and csClients[csPort]:
                csResponse = requestApi(csClients[csPort])
                tags = generateExtraTagStr(extra)
                printCsMetrics(csResponse, 'nbase.cs', ts, tags)
                printCsCompositeMetrics(csResponse, ts, tags)

        sys.stdout.flush()
        time.sleep(collectionInterval)


    for csPort in csClients:
        if csClients[csPort] and csClients[csPort] is not None:
            csClients[csPort].close()
    client.close()

if __name__ == '__main__':
    sys.exit(main())
