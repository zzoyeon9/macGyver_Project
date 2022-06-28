#!/usr/bin/env python

import sys
import time
import subprocess
from time import mktime
from subprocess import Popen, PIPE
from threading import Timer
import re
import os
import pwd

try:
    import pymongo
except ImportError:
    pymongo = None  # This is handled gracefully in main()


HOSTS = ['localhost:27017']
USER = ''
PASS = ''
INTERVAL = 15
ROLES = [
    #"config", "mongos", "replica", "arbiter"
]


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


def parseHostsFromOldVersionSetting(conf):
    hosts = []

    keys = ['config', 'mongos', 'replica']
    for key in keys:
        if key in conf and conf[key]:
            for host in conf[key].split(','):
                hosts.append(host)

    return hosts


def printAsserts(nodeType, timestamp, res):
    for key, value in res['asserts'].items():
        print 'mongo.asserts %d %s node-type=%s assert-type=%s' % (timestamp, value, nodeType, key)


def printMemory(nodeType, timestamp, res):
    for key, value in res['mem'].items():
        if key == 'bits' or key == 'supported' or not str(value).isdigit():
            continue
        print 'mongo.memory.%s %d %s node-type=%s' % (key, timestamp, value, nodeType)


def printOpcounters(nodeType, timestamp, res):
    if 'opcounters' in res:
        for key, value in res['opcounters'].items():
            print 'mongo.opcounters.%s %d %s node-type=%s' % (key, timestamp, value, nodeType)
    if 'opcountersRepl' in res:
        for key, value in res['opcountersRepl'].items():
            print 'mongo.opcountersRepl.%s %d %s node-type=%s' % (key, timestamp, value, nodeType)


def printWiredTigerMem(nodeType, timestamp, res):
    if 'wiredTiger' not in res:
        return

    cache = res['wiredTiger']['cache']

    memMax = int(cache['maximum bytes configured'])
    print 'mongo.wiredTiger.memory.max %d %s node-type=%s' % (timestamp, memMax, nodeType)

    memCur = int(cache['bytes currently in the cache'])
    print 'mongo.wiredTiger.memory.current %d %s node-type=%s' % (timestamp, memCur, nodeType)

    memUsage = memCur * 100.0 / memMax
    print 'mongo.wiredTiger.memory.usage %d %.1f node-type=%s' % (timestamp, memUsage, nodeType)

    metrics = (
        'modified pages evicted',
        'tracked dirty pages in the cache',
        'unmodified pages evicted',
        'maximum bytes configured',
        'bytes currently in the cache'
    )
    printLongstringMetrics('mongo.wiredTiger.cache', metrics, nodeType, timestamp, res['wiredTiger']['cache'])

    metrics = (
        'number of named snapshots created',
        'number of named snapshots dropped',
        'transaction begins',
        'transaction checkpoint currently running',
        'transaction checkpoint generation',
        'transaction checkpoint max time (msecs)',
        'transaction checkpoint min time (msecs)',
        'transaction checkpoint most recent time (msecs)',
        'transaction checkpoint total time (msecs)',
        'transaction checkpoints',
        'transaction failures due to cache overflow',
        'transaction range of IDs currently pinned',
        'transaction range of IDs currently pinned by a checkpoint',
        'transaction range of IDs currently pinned by named snapshots',
        'transaction sync calls',
        'transactions committed',
        'transactions rolled back'
    )
    printLongstringMetrics('mongo.wiredTiger.tx', metrics, nodeType, timestamp, res['wiredTiger']['transaction'])


def printLongstringMetrics(metricPrefix, metrics, nodeType, timestamp, res):
    for metric in metrics:
        if metric in res:
            value = res[metric]
            metric = metric.replace(' ', '_')
            metric = metric.replace('(', '')
            metric = metric.replace(')', '')
            print '%s.%s %d %s node-type=%s' % (metricPrefix, metric, timestamp, value, nodeType)


def printCommonMetrics(metricPrefix, metrics, nodeType, timestamp, res, extraTags = None):
    tags = '' if not extraTags else ' %s' % extraTags

    for metric in metrics:
        cur = res
        try:
            for m in metric.split('.'):
                cur = cur[m]
        except KeyError:
            continue

        print '%s.%s %d %s node-type=%s%s' % (metricPrefix, metric, timestamp, cur, nodeType, tags)


def printCommonMetricsWithAggregation(metricPrefix, metrics, newMetric, nodeType, timestamp, res, extraTags = None):
    aggregated = 0
    tags = '' if not extraTags else ' %s' % extraTags

    for metric in metrics:
        cur = res
        try:
            for m in metric.split('.'):
                cur = cur[m]
        except KeyError:
            continue

        aggregated = aggregated + int(cur)

    if aggregated > 0:
        print '%s.%s %d %s node-type=%s%s' % (metricPrefix, newMetric, timestamp, str(aggregated), nodeType, tags)


def printLockMetrics(metricPrefix, metrics, nodeType, timestamp, res, extraTags = None):
    postfixes = (
        'r', 'w', 'R', 'W'
    )

    for metric in metrics:
        cur = res
        try:
            for m in metric.split('.'):
                cur = cur[m]
        except KeyError:
            continue

        tags = '' if not extraTags else ' %s' % extraTags

        if str(cur).isdigit():
            print '%s.%s %d %s node-type=%s%s' % (metricPrefix, metric, timestamp, cur, nodeType, tags)
            continue

        for postfix in postfixes:
            if postfix in cur:
                lockTypeName = getLockTypeName(postfix)
                value = cur[postfix]
                print '%s.%s %d %s node-type=%s lock-type=%s%s' % (metricPrefix, metric, timestamp, value, nodeType, lockTypeName, tags)


def printGlobalLock(nodeType, timestamp, res):
    if 'globalLock' not in res:
        return

    metrics = (
        'activeClients.readers',
        'activeClients.writers',
        'currentQueue.readers',
        'currentQueue.writers'
    )
    printCommonMetrics('mongo.globalLock', metrics, nodeType, timestamp, res['globalLock'])


def printWiredTigerTx(nodeType, timestamp, res):
    if 'wiredTiger' not in res:
        return

    metrics = (
        'read.out',
        'read.available',
        'read.totalTickets',
        'write.out',
        'write.available',
        'write.totalTickets'
    )
    printCommonMetrics('mongo.wiredTiger.concurrentTransactions', metrics, nodeType, timestamp, res['wiredTiger']['concurrentTransactions'])


def printConnections(nodeType, timestamp, res):
    if 'connections' not in res:
        return

    connCur = res['connections']['current']
    connAvail = res['connections']['available']
    connUsage = connCur * 100.0 / (connCur + connAvail)
    print 'mongo.connections.current %d %s node-type=%s' % (timestamp, connCur, nodeType)
    print 'mongo.connections.available %d %s node-type=%s' % (timestamp, connAvail, nodeType)
    print 'mongo.connections.usage %d %.1f node-type=%s' % (timestamp, connUsage, nodeType)


def printReplicationDelay(nodeType, timestamp, res):
    if 'members' not in res:
        return

    primaryMember = None
    secondaryMembers = []

    members = res['members']
    for member in members:
        if member['stateStr'] == 'PRIMARY':
            primaryMember = member
        elif member['stateStr'] == 'SECONDARY':
            secondaryMembers.append(member)

    if 'self' in primaryMember:
        return

    if primaryMember is not None and len(secondaryMembers) > 0:
        for member in secondaryMembers:
            if 'self' in member:
                delay = datetimeToTimestamp(member['optimeDate']) - datetimeToTimestamp(primaryMember['optimeDate'])
                print 'mongo.replica.replication_delay_sec %d %s node-type=%s' % (timestamp, delay, nodeType)


def printDbStats(nodeType, timestamp, res):
    metrics = (
        'objects',
        'avgObjSize',
        'dataSize',
        'storageSize',
        'numExtents',
        'indexes',
        'indexSize'
    )
    printCommonMetrics('mongo.db', metrics, nodeType, timestamp, res, extraTags = 'db=%s' % res['db'])

    aggMetrics = (
        'dataSize',
        'indexSize'
    )
    printCommonMetricsWithAggregation('mongo.db', aggMetrics, 'dbSize', nodeType, timestamp, res, extraTags = 'db=%s' % res['db'])


def printExtraInfo(nodeType, timestamp, res):
    if 'extra_info' not in res:
        return

    if 'page_faults' in res['extra_info']:
        value = res['extra_info']['page_faults']
        print 'mongo.pageFaults %d %s node-type=%s' % (timestamp, value, nodeType)

    if 'heap_usage_bytes' in res['extra_info']:
        value = res['extra_info']['heap_usage_bytes']
        print 'mongo.heapUsageBytes %d %s node-type=%s' % (timestamp, value, nodeType)


def printLocks(nodeType, timestamp, res):
    if 'locks' not in res:
        return

    metrics = (
        'Collection.acquireCount',
        'Database.acquireCount',
        'Global.acquireCount',
        'Metadata.acquireCount',
        'oplog.acquireCount'
    )
    printLockMetrics('mongo.locks', metrics, nodeType, timestamp, res['locks'])


def printReplicaSetDbStats(timestamp, res):
    if 'raw' not in res:
        return

    metrics = (
        'collections',
        'objects',
        'avgObjSize',
        'dataSize',
        'storageSize',
        'numExtents',
        'indexes',
        'indexSize',
        'fileSize'
    )

    aggMetrics = (
        'dataSize',
        'indexSize'
    )

    for key, item in res['raw'].items():
        rsName = key.split('/', 1)[0]
        extraTags = 'db=%s replica-set=%s' % (item['db'], rsName)
        printCommonMetrics('mongo.rs', metrics, 'replica-set', timestamp, item, extraTags = extraTags)
        printCommonMetricsWithAggregation('mongo.db', aggMetrics, 'dbSize', 'replica-set', timestamp, res, extraTags = extraTags)


def printReplicaSetStats(nodeType, timestamp, res):
    rsName = res['set']
    rsStatus = res['myState']

    for replica in res['members']:
        if 'self' in replica:
            continue

        replicaName = replica['name'].replace(':', '/')
        replicaState = replica['stateStr'].lower()
        if int(replica['health']) == 1:
            replicaHealth = 'online'
        else:
            replicaHealth = 'offline'
        value = replica['pingMs']

        print 'mongo.replica.pingMs %d %s replica-set=%s replica=%s node-type=%s replica-health=%s' % (timestamp, value, rsName, replicaName, replicaState, replicaHealth)


def printMetrics(nodeType, timestamp, res):
    if 'metrics' not in res:
        return

    if 'commands' in res['metrics']:
        commands = res['metrics']['commands']
        for command, stats in commands.items():
            if str(stats).isdigit():
                print 'mongo.metrics.commands.unknown %d %s node-type=%s' % (timestamp, stats, nodeType)
                continue

            tags = (
                'failed', 'total'
            )

            for tag in tags:
                if tag in stats:
                    value = stats[tag]
                print 'mongo.metrics.commands.%s %d %s node-type=%s result=%s' % (command, timestamp, value, nodeType, tag)

    if 'document' in res['metrics']:
        documents = res['metrics']['document']
        for status, stats in documents.items():
            if str(stats).isdigit():
                print 'mongo.metrics.document %d %s node-type=%s status=%s' % (timestamp, stats, nodeType, status)


def printPartInfo(nodeType, timestamp, partInfo):
    if partInfo is not None:
        print 'mongo.datadisk.capacity %d %s node-type=%s mount=%s' % (timestamp, partInfo[2], nodeType, partInfo[1])
        print 'mongo.datadisk.available %d %s node-type=%s mount=%s' % (timestamp, partInfo[3], nodeType, partInfo[1])


def printNetwork(nodeType, timestamp, res):
    keys = ['bytesIn', 'bytesOut', 'numRequests', 'physicalBytesIn', 'physicalBytesOut']
    if 'network' in res:
        for key in keys:
            if key in res['network']:
                print 'mongo.network.%s %d %s node-type=%s' % (key, timestamp, res['network'][key], nodeType)


def getDataPath(conn):
    res = conn.admin.command('getCmdLineOpts')
    if 'parsed' in res and 'storage' in res['parsed'] and 'dbPath' in res['parsed']['storage']:
        return res['parsed']['storage']['dbPath']
    return None


def findDiskPartInfo(findPath):
    if not findPath or len(findPath) == 0:
        return None

    latestFound = None

    p = subprocess.Popen(['df', '-l'], stdout=subprocess.PIPE, shell=True)
    (res, err) = p.communicate()

    arr = res.split('\n')
    for row in arr:
        cols = re.findall(r'\S+', row)
        if len(cols) != 6 or not str(cols[1]).isdigit():
            continue

        part = cols[0]
        capacity = int(cols[1]) * 1024
        avail = int(cols[3]) * 1024
        path = cols[5]
        if findPath.startswith(path):
            latestFound = (part, path, str(capacity), str(avail))

    return latestFound


def getLockTypeName(lockType):
    if lockType == 'w':
        return 'IX-LOCK'
    elif lockType == 'r':
        return 'IS-LOCK'
    elif lockType == 'W':
        return 'X-LOCK'
    elif lockType == 'R':
        return 'S-LOCK'
    else:
        return None


def datetimeToTimestamp(dt):
    timestamp = int(mktime(dt.timetuple()))
    return timestamp


def find_process(process_to_find1, process_to_find2):
    cmd = 'ps -ef | grep "%s" | grep "%s" | grep -v grep' % (process_to_find1, process_to_find2)
    proc = Popen(cmd, shell=True, stderr=PIPE, stdout=PIPE)
    kill_proc = lambda p : p.kill()
    timer = Timer(5, kill_proc, [proc])
    counts = 0
    try:
        timer.start()
        stdout, stderr = proc.communicate()
        rows = stdout.splitlines()
        if (len(rows) > 0):
            for row in rows:
                if row.find(process_to_find1) != -1:
                    counts += 1
    finally:
        timer.cancel()
    return counts


def emit_process(role, proc_name, proc_arg):
    current_time = int(time.time())
    found = find_process(proc_name, proc_arg)
    print 'process.mongo.%s %d %d' % (role, current_time, found)
    sys.stdout.flush()


def main():
    global HOSTS, USER, PASS, ROLES

    drop_privileges()
    if pymongo is None:
        print >>sys.stderr, "error: Python module `pymongo' is missing"
        return 13

    conns = []

    for host in HOSTS:
        hostport = host.split(':')
        try:
            conn = pymongo.MongoClient(host=hostport[0], port=int(hostport[1]), connectTimeoutMS=1000, socketTimeoutMS=3000)
        except pymongo.errors.ServerSelectionTimeoutError as e:
            print >>sys.stderr, "error: %s host = %s, port = %s" % \
                                (e, hostport[0], hostport[1])
            continue

        if not conn:
            print >>sys.stderr, "error: Cannot connect the mongodb server. host = %s, port = %s" % \
                                (hostport[0], hostport[1])
            continue

        if USER:
            try:
                conn.admin.authenticate(USER, PASS, mechanism='DEFAULT')
            except pymongo.errors.OperationFailure as e:
                print >>sys.stderr, "error: %s host = %s, port = %s, user = %s" % \
                                    (e, hostport[0], hostport[1], USER)
                continue

        conns.append(conn)

    if len(conns) == 0 and len(ROLES) == 0:
        print >>sys.stderr, "error: There are no mongodb connections to be monitoring. " \
                            "Please check your mongodb3_conf.py if you should be monitoring."
        return 13

    lastPartInfoCollected = -1

    while True:
        # process monitoring
        for role in ROLES:
            if role == 'replica':
                procName = 'mongod'
                procArg  = 'mongod.conf'
            elif role == 'config':
                procName = 'mongod'
                procArg = 'configsvr'
            elif role == 'mongos':
                procName = 'mongos'
                procArg = ''
            elif role == 'arbiter':
                procName = 'mongod'
                procArg  = 'mongod.conf'
            else:
                continue
            emit_process(role, procName, procArg)

        # metric collection
        for conn in conns:
            timestamp = int(time.time())

            res = conn.admin.command('serverStatus')

            # mongos, mongod
            processType = res['process']
            if 'repl' in res and 'ismaster' in res['repl']:
                if res['repl']['ismaster'] == True:
                    nodeType = 'primary'
                else:
                    nodeType = 'secondary'
            else:
                nodeType = processType

            # collect disk capacity and free space using `df` command
            if lastPartInfoCollected <= 0 or timestamp - lastPartInfoCollected > 60 or not partInfo:
                if nodeType == 'primary' or nodeType == 'secondary':
                    partInfo = findDiskPartInfo(getDataPath(conn))
                    printPartInfo(nodeType, timestamp, partInfo)

            if 'version' in res:
                print 'mongo.version %d 0 node-type=%s version=%s' % (timestamp, nodeType, res['version'])

            printAsserts(nodeType, timestamp, res)
            printMemory(nodeType, timestamp, res)
            printOpcounters(nodeType, timestamp, res)
            printWiredTigerMem(nodeType, timestamp, res)
            printGlobalLock(nodeType, timestamp, res)
            printWiredTigerTx(nodeType, timestamp, res)
            printConnections(nodeType, timestamp, res)
            printExtraInfo(nodeType, timestamp, res)
            printLocks(nodeType, timestamp, res)
            printMetrics(nodeType, timestamp, res)
            printNetwork(nodeType, timestamp, res)
            res = None

            dbs = conn.database_names()

            if processType == 'mongos':
                for db in dbs:
                    dbStats = conn[db].command('dbStats')
                    printReplicaSetDbStats(timestamp, dbStats)

            if processType == 'mongod':
                replStats = conn.admin.command('replSetGetStatus')
                printReplicationDelay(nodeType, timestamp, replStats)
                printReplicaSetStats(nodeType, timestamp, replStats)

                for db in dbs:
                    dbStats = conn[db].command('dbStats')
                    printDbStats(nodeType, timestamp, dbStats)
                    dbStats = None

                replStats = None

            dbs = None

        sys.stdout.flush()
        time.sleep(INTERVAL)

if __name__ == '__main__':
    sys.exit(main())
