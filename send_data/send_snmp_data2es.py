#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
向es中写入snmp仿真数据
数据模板来源(json文件)必须要是经过fiter_data过滤后的(数据形式为[{},{},{}])
因为有多个数据源,json文件统一都放在send_data/json目录下
"""
import os
import sys
import json
import time
import random
from functools import reduce
from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import *

# ----------- 需要修改的参数 -----------
es = Elasticsearch('192.168.10.201')
index_name = 'cc-gossip-4a859fff6e5c4521aab187eee1cfceb8-2018.07.25'
data_type = 'snmp'
json_file_name = 'snmp.data'
# ------------------------------------

reload(sys)
sys.setdefaultencoding('utf-8')

CURRENT_DIR = reduce(lambda x, y: os.path.dirname(x), range(1), os.path.abspath(__file__))
JSON_PATH = os.path.join(CURRENT_DIR, 'jsons')
if not os.path.exists(JSON_PATH):
    os.makedirs(JSON_PATH)
JSON_FILE_PATH = os.path.join(JSON_PATH, json_file_name + '.json')


class SendSnmpData2Es(object):

    def __init__(self):
        pass

    def send_data2es(self):
        doc_list = self.read_jsonfile()
        current_doc_list = self.make_data(doc_list)
        body = []
        for doc in current_doc_list:
            body.append({
                "_index": index_name,
                "_type": data_type,
                "_source": doc
            })
        try:
            success, failed = helpers.bulk(es, body)
            print('success: %s, failed: %s' % (success, failed))
        except TransportError as e:
            if isinstance(e, ConnectionTimeout):
                print('read timed out!')
            elif isinstance(e, ConnectionError):
                print('elasticsearch connection refused!')
            else:
                print('system err')

    @staticmethod
    def read_jsonfile():
        with open(JSON_FILE_PATH, 'r') as load_f:
            doc_list = json.load(load_f, encoding=None)
            print('finish reading, doc count: %s' % (len(doc_list)))
            return doc_list

    @staticmethod
    def make_data(doc_list):
        current_doc_list = []
        t = time.time()
        timestamp_in_seconds = int(t)
        timestamp_in_millisecond = int(round(t * 1000))
        for doc in doc_list:
            doc['guid'] = "internal"
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

            current_doc_list.append(doc)
        return current_doc_list


if __name__ == "__main__":
    send_snmp_data2es = SendSnmpData2Es()
    send_snmp_data2es.send_data2es()