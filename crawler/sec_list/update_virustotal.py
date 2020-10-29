# -*- coding: utf-8 -*-
#!/usr/bin/python
from datetime import datetime
import calendar
import sys
import requests
import time
import csv
import subprocess, threading
from queue import Queue

from elasticsearch import Elasticsearch
from elasticsearch import helpers
import click
import schedule
from logContainer import LogsFunc
import geoip2.database

import socket

API_KEYS = [
    "5428844906b66d738e6dc437583b6a03c3883da477d1a62b9effe608b8a9f7f4",
    "0b6de0f26db606e6280a9291d5e32c685e340e9eae025f6a6b64c2d4b706d8cd",
    "56a61e2cb7b6fcc5796edc3f4e4a23848d735b21886cf64382e785828b1acf15",
    "f67b11a533339372d1a52670cf0f0928ab3e92924afc02b4fa7f6c917802beba",
    "f9230fc02b7897a20685bbad5845ae2ff65fc232a5754ea721477c3f4f28e999",
    "0bd3548986bd61387e2152332dd9b3d2c875021c67c61d87126d482f8e03397f",
    "fb3f577a0ba76d1dccff6ddb4364e754308052fb7e2f8cf0adea43f4075b0e57",
    "7da5d96dd1035ee78d8b9a80a195974e3672f96dfdc4a91b9180ac2509c58e11",
    "80a7e63d8244f00251ae9a1de8f94be8297d64a3ab0e2d98d04694246b5ababf"
]

queue = {
    "available_key": Queue(), # key
    "wait_key": Queue()  # key, timestamp
}

def wait_key_worker():
    for key in API_KEYS:
        queue["available_key"].put(key)
    while True:
        key, t1 = queue["wait_key"].get()
        t2 = calendar.timegm(time.gmtime()) 
        diff_t = t2 -t1
        #print("t1 {}, t2 {}, diff {}".format(t1, t2, diff_t))
        if diff_t < 15:
            time.sleep(15 - diff_t)
        queue["available_key"].put(key)
        queue["wait_key"].task_done()

def get_key():
    key = queue["available_key"].get()
    queue["available_key"].task_done()
    t1 = calendar.timegm(time.gmtime()) 
    queue["wait_key"].put((key, t1))
    return key

def get_domain_list_csv():
    csvfile = open('top-1m.csv', newline='')
    domain_list = []
    for row in csvfile:
        row = row.replace('\n', '').split(',')
        rank = int(row[0])
        if rank < 114841: 
            continue
        domain = row[1]

        domain_list.append({
            "rank": rank,
            "domain": domain
        })

    csvfile.close()
    return domain_list

def get_domain_list():
    query = {
        "query" : {
            "bool": {
                "must_not": {
                    "exists": {
                        "field": "virustotal"
                    }
                }
            }
        },
        "sort": {
            "rank": {
                "order": "asc"
            }
        },
        "_source": ["rank", "domain"],
        "size": 5000
    }
    es_result = helpers.scan(
        client=ES_ip,
        query=query,
        scroll="5m",
        index="sec_list*",
        timeout="1m"
    )
    domain_list = []
    for r in es_result:
        domain = r["_source"]
        domain["_id"] = r["_id"]
        domain_list.append(domain)
        
    return domain_list

def is_ip(ip):
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False

def add_virustotal(json): 
    domain = json["domain"]
    params = {
        "apikey": get_key(),
        "url": domain
    }
    res = requests.post("https://www.virustotal.com/vtapi/v2/url/scan", params)
    _json = res.json()

    params = {
        "apikey": get_key(),
        "resource": _json["scan_id"]
    }
    res = requests.get("https://www.virustotal.com/vtapi/v2/url/report", params)
    json["virustotal"] = res.json()

    params = {
        "apikey": get_key(),
        "domain": domain
    }
    res = requests.get("https://www.virustotal.com/vtapi/v2/domain/report", params)
    _json = res.json()
    json["virustotal"]["subdomains"] = _json.get("subdomains", [])
    json["virustotal"]["domain_siblings"] = _json.get("domain_siblings", [])
    now_time = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    #print('{} rank {}'.format(now_time, json["rank"]))

def update_virustotal():
    now_time = datetime.now().strftime("%Y-%m-%d_%H%M")
    print('{} start'.format(now_time))
    domain_list = get_domain_list()
    print("total {}".format(len(domain_list)))
    i = 0 
    for d in domain_list:
        i = i + 1
        try:
            rank = d["rank"]
            domain = d["domain"]
            query = {
                "query": {
                    "term": {
                        "domain.keyword": domain
                    }
                }
            }

            res = ES_ip.search(index = "sec_list_*", body = query)
            if res["hits"]["total"] == 0:
                continue
            index = res["hits"]["hits"][0]["_index"]
            doc_type = res["hits"]["hits"][0]["_type"]
            json = res["hits"]["hits"][0]["_source"]
            add_virustotal(json)
            timestamp = calendar.timegm(time.gmtime()) 
            json["last_timestamp"] = timestamp
            ES_ip.index(index = index, doc_type = doc_type, id = domain, body = json)
            if i % 1000 == 1:
                now_time = datetime.now().strftime("%Y-%m-%d_%H%M")
                print('{} update virustotal {}'.format(now_time, i))
        except Exception as e:
            print("error: {}".format(domain))
            print(e)
    now_time = datetime.now().strftime("%Y-%m-%d_%H%M")
    print('{} finish'.format(now_time))

@click.command()
@click.option('--es_ip', type=str,default='211.23.163.51:59200')
@click.option('--sched_period', type=float,default=10080)#單位為分鐘
def run(es_ip,sched_period):
    global ES_ip
    ES_ip = Elasticsearch(es_ip)
    '''log紀錄執行狀況'''
    global logsFunction
    logsFunction = LogsFunc("whitelist")

    t = threading.Thread(target=wait_key_worker)
    t.start()

    while True:
        update_virustotal()
        time.sleep(1)

if __name__ == '__main__':
    run()
