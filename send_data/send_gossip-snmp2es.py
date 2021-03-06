#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
向es中写入snmp仿真数据
数据模板来源(.txt文件)必须要是经过filter_data过滤后的
因为有多个数据源,.txt文件统一都放在send_data/data目录下

*/1 * * * *  python /home/wenyuan/es_replay/send_data/send_gossip-snmp2es.py >/dev/null 2>&1
"""
import os
import json
import time
import random
from functools import reduce
from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import *
import sys

reload(sys)
sys.setdefaultencoding('utf-8')

# ----------- 需要修改的参数 -----------
es_host = '192.168.10.201'
token = '4a859fff6e5c4521aab187eee1cfceb8'
appname = 'gossip'
doc_type = 'snmp'
index_name = 'cc-{appname}-{doc_type}-{token}-{suffix}'.format(
    appname=appname,
    doc_type=doc_type,
    token=token,
    suffix=time.strftime('%Y.%m.%d')
)
data_file_name = 'snmp.data.txt'
request_body_size = 100
# ------------------------------------

CURRENT_DIR = reduce(lambda x, y: os.path.dirname(x), range(1), os.path.abspath(__file__))
DATA_DIR = os.path.join(CURRENT_DIR, 'data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
DATA_FILE_PATH = os.path.join(DATA_DIR, data_file_name)


def execute_task():
    with open(DATA_FILE_PATH, 'r') as f:
        doc_list = []
        line = f.readline()
        while line:
            line = line.strip('\n')
            doc_content = json.loads(line, encoding='utf-8')
            doc_list.append(doc_content)
            if len(doc_list) >= request_body_size:
                current_doc_list = make_data(doc_list)
                send_data2es(current_doc_list)
                doc_list = []
            line = f.readline()
        if doc_list:
            current_doc_list = make_data(doc_list)
            send_data2es(current_doc_list)


def send_data2es(current_doc_list):
    actions = []
    for doc in current_doc_list:
        actions.append({
            '_op_type': 'index',
            '_index': index_name,
            '_type': doc_type,
            '_source': doc
        })
    try:
        es = Elasticsearch(es_host)
        success, failed = helpers.bulk(client=es, actions=actions)
        print('success: %s, failed: %s' % (success, failed))
    except TransportError as e:
        if isinstance(e, ConnectionTimeout):
            print('Read timed out!')
        elif isinstance(e, ConnectionError):
            print('Elasticsearch connection refused')
        else:
            print('System err')


def make_data(doc_list):
    current_doc_list = []
    t = time.time()
    timestamp_in_seconds = int(t)
    timestamp_in_millisecond = int(round(t * 1000))
    for doc in doc_list:
        doc['guid'] = token
        doc['@timestamp'] = timestamp_in_millisecond
        doc['dawn_ts'] = timestamp_in_millisecond * 1000
        # todo...符合24h内正态分布,先ugly design
        if time.strftime('%H') in ['9', '10', '11', '14', '15', '16']:
            cpu_utilization = round(random.uniform(30, 50), 2)
            mem_utilization = round(random.uniform(30, 80), 2)
        elif time.strftime('%H') in ['0', '1', '2', '3', '4', '5', '6']:
            cpu_utilization = round(random.uniform(10, 30), 2)
            mem_utilization = round(random.uniform(10, 30), 2)
        else:
            cpu_utilization = round(random.uniform(30, 60), 2)
            mem_utilization = round(random.uniform(30, 40), 2)
        doc['snmp']['cpuUtilization'] = cpu_utilization
        doc['snmp']['memUtilization'] = mem_utilization
        if_table_stats = doc['snmp']['ifTableStats']
        for each_if_stats in if_table_stats:
            if each_if_stats['ifOperStatus'] != 1:
                continue
            if time.strftime('%H') in ['9', '10', '11', '14', '15', '16']:
                in_bytes = int(random.uniform(5000, 8000))
                out_bytes = int(random.uniform(30000, 50000))
                in_pkts = int(random.uniform(80, 150))
                out_pkts = int(random.uniform(200, 500))
            elif time.strftime('%H') in ['0', '1', '2', '3', '4', '5', '6']:
                in_bytes = int(random.uniform(100, 500))
                out_bytes = int(random.uniform(800, 1500))
                in_pkts = int(random.uniform(10, 20))
                out_pkts = int(random.uniform(10, 20))
            else:
                in_bytes = int(random.uniform(3000, 5000))
                out_bytes = int(random.uniform(10000, 20000))
                in_pkts = int(random.uniform(50, 80))
                out_pkts = int(random.uniform(10, 30))
            each_if_stats['ifInOctets'] = in_bytes
            each_if_stats['ifOutOctets'] = out_bytes
            each_if_stats['ifInNUcastPkts'] = in_pkts
            each_if_stats['ifOutUcastPkts'] = out_pkts

        if_number = doc['snmp']['ifNumber']
        ipnet_table_stats = doc['snmp']['ipNetToMediaTableStats']
        for index, each_ifnet in enumerate(ipnet_table_stats):
            each_ifnet['ipNetToMediaIfIndex'] = min(index + 1, if_number)

        current_doc_list.append(doc)
    return current_doc_list


if __name__ == "__main__":
    execute_task()
