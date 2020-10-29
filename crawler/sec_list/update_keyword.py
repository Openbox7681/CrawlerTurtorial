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
import pandas as pd
import numpy as np

from elasticsearch import Elasticsearch
import click
import schedule
from logContainer import LogsFunc


def update_keyword():
    now_time = datetime.now().strftime("%Y-%m-%d_%H%M")
    print('{} start'.format(now_time))
    df = pd.read_excel("2018-11-21OT_riskReport.xlsx", sheet_name=1, keep_default_na=False)
    data = np.array(df).tolist()

    for row in data:
        try:
            json = {
                "name": row[0],
                "vendor": row[1],
                "product": row[2],
                "category": row[3],
                "os": row[4]
            }
            id = "{}-{}".format(json["vendor"], json["product"]).lower()
            print(id)
            print(json)
    
            ES_ip.index(index = ES_index, doc_type = "medical", id = id, body = json)
        except Exception as e:
            print(e)
            continue
    now_time = datetime.now().strftime("%Y-%m-%d_%H%M")
    print('{} finish'.format(now_time))

@click.command()
@click.option('--es_ip', type=str,default='211.23.163.51:59200')
@click.option('--es_index', type=str,default='sec_keyword_medical')
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
    logsFunction = LogsFunc("keyword")

    update_keyword()

if __name__ == '__main__':
    run()
