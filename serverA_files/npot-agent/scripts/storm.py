#!/usr/bin/env python

import httplib
import sys
import time
import os
import pwd

try:
    import json
except ImportError:
    json = None

COLLECTION_INTERVAL = 15
STORM_HOST = "localhost"
STORM_PORT = 8080

CLUSTER_KEYS = (
    'slotsFree', 'topologies', 'supervisors', 'tasksTotal', 'slotsUsed', 'slotsTotal', 'executorsTotal'
)

SUPERVISOR_KEYS = (
    'totalMem', 'totalCpu', 'usedCpu', 'usedMem', 'slotsUsed', 'slotsTotal', 'uptimeSeconds'
)

TOPOLOGY_KEYS = (
    'assignedTotalMem', 'requestedMemOnHeap', 'assignedMemOnHeap', 'workersTotal', 'requestedMemOffHeap',
    'tasksTotal', 'requestedCpu', 'replicationCount', 'executorsTotal', 'assignedCpu', 'assignedMemOffHeap',
    'requestedTotalMem', 'uptimeSeconds'
)

SPOUT_KEYS = (
    'emitted', 'tasks', 'failed', 'executors', 'transferred', 'acked'
)

SPOUT_STATS_KEYS = (
    'completeLatency',
)

BOLT_KEYS = (
    'emitted', 'tasks', 'failed', 'executors', 'transferred', 'acked', 'executed'
)

BOLT_STATS_KEYS = (
    'processLatency', 'executeLatency', 'capacity'
)

TOPOLOGIES_KEYS = (
    'emitted', 'transferred', 'acked', 'failed'
)

TOPOLOGIES_STATS_KEYS = (
    'completeLatency',
)

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

def print_cluster(json_data, timestamp):
    for key in CLUSTER_KEYS:
        if not key in json_data:
            continue
        value = json_data[key]
        print "storm.cluster.%s %d %s" % (key, timestamp, value)


def print_nimbus(json_data, timestamp):
    if not 'nimbuses' in json_data:
        return
    for index, item in enumerate(json_data['nimbuses'], start=0):
        host = item['host']
        port = item['port']
        version = item['version']
        if 'status' not in item or not item['status'] or item['status'] == 'Offline':
            continue
        uptime = item['nimbusUpTimeSeconds']
        print "storm.nimbus.nimbusUpTimeSeconds %d %s node-host=%s node-port=%s status=%s version=%s" \
              % (timestamp, uptime, host, port, item['status'].replace(' ', '_'), version)


def print_supervisor(json_data, timestamp):
    if not 'supervisors' in json_data:
        return

    for index, item in enumerate(json_data['supervisors'], start=0):
        node_id = item['id']
        host = item['host']
        for key in SUPERVISOR_KEYS:
            if not key in item:
                continue
            value = item[key]
            print "storm.supervisor.%s %d %s id=%s node-host=%s" % (key, timestamp, value, node_id, host)


def print_topology(json_data, timestamp):
    if not 'topologies' in json_data:
        return

    for index, item in enumerate(json_data['topologies'], start=0):
        node_id = item['id']
        if 'status' not in item or not item['status']:
            continue
        for key in TOPOLOGY_KEYS:
            if not key in item:
                continue
            value = item[key]
            print "storm.topology.%s %d %s id=%s status=%s" % (key, timestamp, value, node_id, item['status'].replace(' ', '_'))


def print_topologies(json_data, topo_id, timestamp):
    metric_partial = 'topologyStats'
    if not metric_partial in json_data:
        return

    for index, item in enumerate(json_data[metric_partial], start=0):
        if not 'window' in item:
            continue

        if item['window'] == '600':
            keys = TOPOLOGIES_STATS_KEYS
        elif item['window'] == ':all-time':
            keys = TOPOLOGIES_KEYS
        else:
            continue

        for key in keys:
            if not key in item:
                continue
            elif item[key] is None:
                value = 0
            else:
                value = item[key]
            print "storm.topology.%s %d %s topo-id=%s" % (key, timestamp, str(value), topo_id)


def print_component(json_data, topo_id, timestamp, metric_map, component):
    metric_partial = component + 's'

    if not metric_partial in json_data:
        return

    for index, item in enumerate(json_data[metric_partial], start=0):
        comp_id = item[component + 'Id']
        for key in metric_map:
            if not key in item:
                continue
            elif item[key] is None:
                value = 0
            else:
                value = item[key]
            print "storm.%ss.%s %d %s topo-id=%s %s-id=%s" \
                  % (component, key, timestamp, str(value), topo_id, component, comp_id)


def request_url(client, uri):
    client.request('GET', uri)
    resp = client.getresponse().read()
    return json.loads(resp)


def extract_topologies(json_data):
    topologies = {}
    if not 'topologies' in json_data:
        return topologies
    for index, item in enumerate(json_data['topologies'], start=0):
        topology_id = item['id']
        topologies[topology_id] = item
    return topologies


def print_component_detail(client, json_data, topo_id, timestamp, metric_map, component, window):
    metric_partial = component + 's'

    if not metric_partial in json_data:
        return

    window_query = ''
    if window is not None:
        window_query = '?window=%d' % window

    for index, item in enumerate(json_data[metric_partial], start=0):
        comp_id = item[component + 'Id']
        res = request_url(client, '/api/v1/topology/' + topo_id + '/component/' + comp_id + window_query)
        if 'executorStats' in res:
            for index, item in enumerate(res['executorStats'], start=0):
                exe_id = item['id'].replace("[", "").replace("]", "")
                for key in metric_map:
                    if not key in item:
                        continue
                    elif item[key] is None:
                        value = 0
                    else:
                        value = item[key]
                    print "storm.%s.%s %d %s topo-id=%s %s-id=%s exe-id=%s" \
                          % (component, key, timestamp, str(value), topo_id, component, comp_id, exe_id)

        if 'spoutSummary' in res:
            summaryKey = 'spoutSummary'
        elif 'boltStats' in res:
            summaryKey = 'boltStats'
        else:
            continue

        for index, item in enumerate(res[summaryKey], start=0):
            if not 'window' in item:
                continue
            if window == 600 and item['window'] == '600':
                for key in metric_map:
                    if not key in item:
                        continue
                    elif item[key] is None:
                        value = 0
                    else:
                        value = item[key]
                    print "storm.%ss.%s %d %s topo-id=%s %s-id=%s" % (component, key, timestamp, str(value), topo_id, component, comp_id)


def main():
    drop_privileges()
    if json is None:
        print >>sys.stderr, "error: Python module `json' is missing"
        return 13

    client = httplib.HTTPConnection(STORM_HOST, STORM_PORT)

    while True:
        ts = int(time.time())

        res = request_url(client, '/api/v1/cluster/summary')
        print_cluster(res, ts)

        res = request_url(client, '/api/v1/nimbus/summary')
        print_nimbus(res, ts)

        res = request_url(client, '/api/v1/supervisor/summary')
        print_supervisor(res, ts)

        res = request_url(client, '/api/v1/topology/summary')
        print_topology(res, ts)
        if 'topologies' in res:
            for index, item in enumerate(res['topologies'], start=0):
                topo_id = item['id']
                res = request_url(client, '/api/v1/topology/' + topo_id)
                print_topologies(res, topo_id, ts)

                print_component(res, topo_id, ts, SPOUT_KEYS, 'spout')
                print_component_detail(client, res, topo_id, ts, SPOUT_KEYS, 'spout', None)      # accumulated
                print_component_detail(client, res, topo_id, ts, SPOUT_STATS_KEYS, 'spout', 600) # 10m aggregated

                print_component(res, topo_id, ts, BOLT_KEYS, 'bolt')
                print_component_detail(client, res, topo_id, ts, BOLT_KEYS, 'bolt', None)        # accumulated
                print_component_detail(client, res, topo_id, ts, BOLT_STATS_KEYS, 'bolt', 600)   # 10m aggregated

        sys.stdout.flush()
        time.sleep(COLLECTION_INTERVAL)

    client.close()


if __name__ == '__main__':
    sys.exit(main())
