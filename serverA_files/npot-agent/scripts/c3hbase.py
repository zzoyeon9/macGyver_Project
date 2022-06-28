#!/usr/bin/env python
#-*- coding: utf-8 -*-

import httplib
import sys
try:
    import json
except ImportError:
    json = None
try:
    from collections import OrderedDict  # New in Python 2.7
except ImportError:
    from ordereddict import OrderedDict  # Can be easy_install'ed for <= 2.6
import time
import re
import urllib2

CLUSTER = '<cluster>'
HBASE_MASTER_WEB = '<master-ui-host>:<master-ui-port>'
NPOT_HOST = "npot-tsw.navercorp.com"
NPOT_PORT = "10041"
NPOT_TENANT = "<tenant-id>:<tenant-auth>"
EXCLUDED_KEYS = (
    "Name",
    "name"
)

EMIT_REGIONS = False
INTERVAL = 15
EXCLUDED_CONTEXTS = ("master")
REGION_METRIC_PATTERN = re.compile(r"[N|n]amespace_(.*)_table_(.*)_region_(.*)_metric_(.*)")
REGION_ITEM_PATTERN = re.compile(r'([^/]+)/rs-status')


class HadoopHttp(object):
    def __init__(self, service, daemon, host, port, uri="/jmx"):
        self.service = service
        self.daemon = daemon
        self.port = port
        self.host = host
        self.uri = uri
        self.server = httplib.HTTPConnection(self.host, self.port)
        self.server.auto_open = True

    def request(self):
        try:
            self.server.request('GET', self.uri)
            resp = self.server.getresponse().read()
        # except:
        #     resp = '{}'
        finally:
            self.server.close()
        return json.loads(resp)

    def poll(self):
        """
        Get metrics from the http server's /jmx page, and transform them into normalized tupes

        @return: array of tuples ([u'Context', u'Array'], u'metricName', value)
        """
        json_arr = self.request().get('beans', [])
        kept = []
        for bean in json_arr:
            if (not bean['name']) or (not "name=" in bean['name']):
                continue
            #split the name string
            context = bean['name'].split("name=")[1].split(",sub=")
            # Create a set that keeps the first occurrence
            context = OrderedDict.fromkeys(context).keys()
            # lower case and replace spaces.
            context = [c.lower().replace(" ", "_") for c in context]
            # don't want to include the service or daemon twice
            context = [c for c in context if c != self.service and c != self.daemon]

            for key, value in bean.iteritems():
                if key in EXCLUDED_KEYS:
                    continue
                if not is_numeric(value):
                    continue
                kept.append((context, key, value))
        return kept

    def collect_metric(self, context, current_time, metric_name, value, tag_dict):
        tag_string = '{%s}' % ",".join(['"' + k + '":"' + v + '"' for k, v in tag_dict.iteritems()])
        return '{"metric":"%s.%s.%s.%s","timestamp":%d,"value":%d,"tags":%s}' % (self.service, self.daemon, ".".join(context), metric_name, current_time, value, tag_string)

    def collect(self, current_timestamp):
        pass


class HBaseMaster(HadoopHttp):
    def __init__(self, host, port):
        super(HBaseMaster, self).__init__('hbase', 'master', host, port)

    def collect(self, current_time):
        global CLUSTER
        queue = []
        metrics = self.poll()
        tag_dict = {"cluster": CLUSTER, "host": self.host}
        for context, metric_name, value in metrics:
            if any(c in EXCLUDED_CONTEXTS for c in context):
                continue
            dp = self.collect_metric(context, current_time, metric_name, value, tag_dict)
            if dp is not None:
                queue.append(dp)
        return queue


class HBaseRegionserver(HadoopHttp):
    def __init__(self, host, port):
        super(HBaseRegionserver, self).__init__("hbase", "regionserver", host, port)

    def collect_region_metric(self, context, current_time, full_metric_name, value):
        global CLUSTER
        match = REGION_METRIC_PATTERN.match(full_metric_name)
        if not match:
            err("Error splitting %s" % full_metric_name)
            return None

        namespace = match.group(1)
        table = match.group(2)
        region = match.group(3)
        metric_name = match.group(4)
        tag_dict = {"cluster": CLUSTER, "namespace": namespace, "table": table, "region": region, "host": self.host}

        if any(not v for k,v in tag_dict.iteritems()):
            err("Error splitting %s" % full_metric_name)
            return None
        else:
            return self.collect_metric(context, current_time, metric_name, value, tag_dict)

    def collect(self, current_timestamp):
        global EMIT_REGIONS, CLUSTER

        queue = []
        metrics = self.poll()
        for context, metric_name, value in metrics:
            if any(c in EXCLUDED_CONTEXTS for c in context):
                continue
            tag_dict = {"cluster": CLUSTER, "host": self.host}
            dp = None
            if any(c == "regions" for c in context):
                if metric_name == 'numRegions':
                    dp = self.collect_metric(context, current_timestamp, metric_name, value, tag_dict)
                elif EMIT_REGIONS:
                    dp = self.collect_region_metric(context, current_timestamp, metric_name, value, tag_dict)
            else:
                dp = self.collect_metric(context, current_timestamp, metric_name, value, tag_dict)
            if dp is not None:
                queue.append(dp)
        return queue


class NpotSender():
    def __init__(self, host, port, tenant):
        self.host = host
        self.port = port
        self.conn = httplib.HTTPConnection(host, port)
        self.headers = {"Content-type": "application/json", "Auth": tenant}

    def send(self, dps):
        body = "[%s]" % (",".join(dps))
        for i in range(3):
            try:
                self.conn.request("POST", "/api/put", body, self.headers)
                #self.conn.set_debuglevel(1)
                res = self.conn.getresponse()
                res.read()
                break
            except:
                time.sleep(1)
                self.conn = httplib.HTTPConnection(self.host, self.port)
                continue


def is_numeric(value):
    return isinstance(value, (int, long, float)) and not isinstance(value, bool)


def err(msg):
    print >> sys.stderr, msg


def getRegionHosts():
    global HBASE_MASTER_WEB
    url = 'http://%s/master-status' % HBASE_MASTER_WEB
    res = urllib2.urlopen(url)
    body = res.read()
    return re.findall('([^/]+)/rs-status', body)


def main(args):
    global HBASE_MASTER_WEB, NPOT_HOST, NPOT_PORT, NPOT_TENANT
    regionServers = getRegionHosts()
    counts = 0
    rspool = {}

    sender = NpotSender(NPOT_HOST, NPOT_PORT, NPOT_TENANT)

    hmasterHostPort = HBASE_MASTER_WEB.split(':')
    hmaster = HBaseMaster(hmasterHostPort[0], hmasterHostPort[1])

    while True:
        emit_timestamp = int(time.time())
        sender.send(hmaster.collect(emit_timestamp))

        for rs in regionServers:
            if rs not in rspool:
                hostPort = rs.split(':')
                hregion = HBaseRegionserver(hostPort[0], int(hostPort[1]))
                rspool[rs] = hregion
            else:
                hregion = rspool[rs]
            sender.send(hregion.collect(emit_timestamp))

        sleep_time = INTERVAL - (int(time.time()) - emit_timestamp)
        if sleep_time <= 1:
            sleep_time = 1
        elif sleep_time >= INTERVAL:
            sleep_time = INTERVAL
        time.sleep(sleep_time)
        counts = counts + 1
        if counts % int(300.0 / INTERVAL) == 0:
            regionServers = getRegionHosts()
            rspool = {}

if __name__ == "__main__":
    sys.exit(main(sys.argv))
