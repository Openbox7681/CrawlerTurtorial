# -*- coding: utf-8 -*-
#!/usr/bin/python
from datetime import datetime
import calendar
import sys
import requests
import time
import csv
import subprocess

from elasticsearch import Elasticsearch
from elasticsearch import helpers
import click
import schedule
from logContainer import LogsFunc
import geoip2.database

import socket

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
                        "field": "geoip"
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

def modify_names_field(json):
    names = json.get("names")
    if names == None:
        return json
    del json["names"]
    json["name"] = names.get("en")
    return json

def add_geoip(json): 
    json["geoip"] = []
    for ip in json["ip"]:
        if is_ip(ip) == False:
            continue
        try:
            city = geo["city"](ip).__dict__["raw"]
            isp = geo["isp"](ip).__dict__["raw"]
            domain = geo["domain"](ip).__dict__["raw"]
        except Exception as e:
            print(e)
            continue

        if isp.get("ip_address") != None:
            del isp["ip_address"]
        if domain.get("ip_address") != None:
            del domain["ip_address"]
        json["geoip"].append({
            "ip_address": ip,
            "continent": modify_names_field(city.get("continent", {})),
            "country": modify_names_field(city.get("country", {})),
            "registered_country": modify_names_field(city.get("registered_country", {})),
            "city": modify_names_field(city.get("city", {})),
            "domain": domain,
            "isp": isp,
            "location": city.get("location", {}),
            "postal": city.get("postal", {}),
            "subdivisions": [modify_names_field(s) for s in city.get("subdivisions", [])]
        })

def update_geoip():
    now_time = datetime.now().strftime("%Y-%m-%d_%H%M")
    print('{} start'.format(now_time))
    domain_list = get_domain_list()
    total = len(domain_list)
    print("total {}".format(total))
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
            add_geoip(json)
            timestamp = calendar.timegm(time.gmtime()) 
            json["last_timestamp"] = timestamp
            ES_ip.index(index = index, doc_type = doc_type, id = domain, body = json)
            if i % 1000 == 1:
                now_time = datetime.now().strftime("%Y-%m-%d_%H%M")
                print('{} update geoip {}'.format(now_time, i))
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
    global geo

    while True:
        city_reader = geoip2.database.Reader('./GeoIP2-City.mmdb') 
        domain_reader = geoip2.database.Reader('./GeoIP2-Domain.mmdb') 
        isp_reader = geoip2.database.Reader('./GeoIP2-ISP.mmdb') 
        geo = {
            "city": city_reader.city,
            "domain": domain_reader.domain,
            "isp": isp_reader.isp
        }
        update_geoip()
        city_reader.close()
        domain_reader.close()
        isp_reader.close()
        time.sleep(1)

if __name__ == '__main__':
    run()
