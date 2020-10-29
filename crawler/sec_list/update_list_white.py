# -*- coding: utf-8 -*-
#!/usr/bin/python
from datetime import datetime
import calendar
import json
import sys
import requests
import time
import csv
import subprocess

from elasticsearch import Elasticsearch
import click
import schedule
from logContainer import LogsFunc

def get_ip(domain): 
    ip = []
    i = 0
    while True:
        i = i + 1
        try:
            ip_list = subprocess.check_output(['dig', '+short', domain]).decode("utf-8").split('\n')
            for _ip in ip_list[0:len(ip_list)-1]:
                if _ip in ip:
                    continue
                ip.append(_ip)
            break
            if len(ip_list) > 2 or (i > 5 and i >= 2*len(ip)):
                break
        except Exception as e:
            print(e)
            break
    return ip

def update_domain():
    now_time = datetime.now().strftime("%Y-%m-%d_%H%M")
    print('{} start'.format(now_time))
    with open('top-1m.csv', newline='') as csvfile:
        for row in csvfile:
            row = row.replace('\r', '').replace('\n', '').split(',')
            rank = int(row[0])
            domain = row[1]
            ip = get_ip(domain)

            timestamp = calendar.timegm(time.gmtime()) 
            json = {
                "domain": domain,
                "rank": int(rank),
                "ip": ip,
                "first_timestamp": timestamp,
                "last_timestamp": timestamp
            }

            query = {
                "query": {
                    "term": {
                        "domain.keyword": domain
                    }
                }
            }

            #res = ES_ip.search(index = ES_index, body = query)
            res = ES_ip.search(index = "test_sec_list_white", body = query)
            if res["hits"]["total"] > 0:
                oldJson = res["hits"]["hits"][0]["_source"]
                json["first_timestamp"] = oldJson.get("first_timestamp", timestamp)
                json["geoip"] = oldJson.get("geoip")
                json["virustotal"] = oldJson.get("virustotal")

            ES_ip.index(index = ES_index, doc_type = "white", id = domain, body = json)
            if rank % 1000 == 1:
                now_time = datetime.now().strftime("%Y-%m-%d_%H%M")
                print('{} update rank {}'.format(now_time, rank))
    now_time = datetime.now().strftime("%Y-%m-%d_%H%M")
    print('{} finish'.format(now_time))

@click.command()
@click.option('--es_ip', type=str,default='211.23.163.51:59200')
@click.option('--es_index', type=str,default='sec_list_white')
@click.option('--sched_period', type=float,default=10080)#單位為分鐘
def run(es_ip, es_index, sched_period):
    global ES_ip
    ES_ip = Elasticsearch(es_ip)
    global ES_index
    ES_index = es_index
    if not ES_ip.indices.exists(index = ES_index):
        ES_ip.indices.create(index = ES_index)
    '''log紀錄執行狀況'''
    global logsFunction
    logsFunction = LogsFunc("whitelist")
    schedule.every(sched_period).minutes.do(update_domain)
    schedule.run_all()  # 即時執行


    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    run()
