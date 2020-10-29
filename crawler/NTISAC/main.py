# -*- coding: utf-8 -*-
#!/usr/bin/python3
from datetime import datetime
import calendar
import json
import sys
import requests
import time

from elasticsearch import Elasticsearch
import click
import schedule

from logContainer import LogsFunc

'''爬取時間範圍'''
def get_time():
    t = datetime.now()
    year = t.year
    month = t.month

    if (month == 1):
        '''現在是1月的時候 爬到去年12月'''
        start_month = str(year-1)+'/12'
        logsFunction.appendWrite('start month: '+start_month)
        start_month = datetime.strptime(start_month, '%Y/%m')
        start_month = calendar.timegm(datetime.timetuple(start_month)) * 1000

        end_month = str(year)+"/"+str(month)
        logsFunction.appendWrite('end month: '+ end_month)

        '''取得當月最後一天'''
        end_month = t.replace(day = calendar.monthrange(year, month)[1])
        end_month = calendar.timegm(datetime.timetuple(end_month)) * 1000

    else:
        '''抓當月以及上一個月的'''
        start_month = str(year)+"/"+str(month-1)
        logsFunction.appendWrite('start month: '+start_month)
        start_month = datetime.strptime(start_month, '%Y/%m')
        start_month = calendar.timegm(datetime.timetuple(start_month)) * 1000

        end_month = str(year)+"/"+str(month)
        logsFunction.appendWrite('end month: '+end_month)

        '''取得當月最後一天'''
        end_month = t.replace(day = calendar.monthrange(year, month)[1])
        end_month = calendar.timegm(datetime.timetuple(end_month)) * 1000

    return start_month, end_month

'''撈取ICS-CERT資料'''
def get_ICSCert_data(time):
    query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "range": {
                            "publish_date": {
                                "gte": time[0], "lte": time[1]
                            }
                        }
                    }
                ]
            }
        }
    }
    response = ES_ip.search(index="sec_icscert-*",
                         scroll='4m', size=300, body=query)
    logsFunction.appendWrite('ICS_CERT資料筆數： '+str(len(response["hits"]["hits"])))

    sid = response['_scroll_id']
    scroll_size = response['hits']['total']
    analysis(response)
    while (scroll_size > 0):
        response = ES_ip.scroll(scroll_id=sid, scroll='2m')
        sid = response['_scroll_id']
        scroll_size = len(response['hits']['hits'])
        '''save information'''
        analysis(response)

'''整併報告與漏洞細節'''
def analysis(response):
    '''取得ICS-CERT報告'''
    for length in range(0, len(response["hits"]["hits"])):

        logsFunction = LogsFunc("NTISAC")        
        if "url" in response["hits"]["hits"][length]["_source"]:
            logsFunction.appendWrite((response["hits"]["hits"][length]["_source"]["url"]))            
        else:
            logsFunction.appendWrite("Unknown")            

        if "background" in response["hits"]["hits"][length]["_source"]:
            '''1. 取得欄位：產業別'''        
            Critical_Infrastructure_Sectors = (str(
                response["hits"]["hits"][length]["_source"]["background"][0]["Critical_Infrastructure_Sectors"]).lower())
            # logsFunction.appendWrite('產業別： '+(Critical_Infrastructure_Sectors))

        find_industry = False
        d = response["hits"]["hits"][length]  
        query = {
                    "query": {
                        "term": {
                            "_id": d["_id"]
                            }
                        }
                    }        
        try:     
            '''是否為政府基礎關鍵設施'''
            if Critical_Infrastructure_Sectors.find("critical manufacturing") > -1 or Critical_Infrastructure_Sectors.find("government") > -1:
                find_industry = True
                logsFunction.appendWrite('產業別是政府基礎關鍵設施')                                                               
                res = ES_ip.search(index = 'sec_info_gov', body = query)
                if res["hits"]["total"] == 0:
                    ES_ip.index(index = 'sec_info_gov', doc_type = "info_government", id = d["_id"], body = d["_source"])                        
            
            '''是否為金融基礎關鍵設施'''
            if Critical_Infrastructure_Sectors.find("financial services") > -1:
                find_industry = True
                logsFunction.appendWrite('產業別是金融基礎關鍵設施')                                                               
                res = ES_ip.search(index = 'sec_info_finance', body = query)
                if res["hits"]["total"] == 0:
                    ES_ip.index(index = 'sec_info_finance', doc_type = "info_finance", id = d["_id"], body = d["_source"])                        
            
            '''是否為5g基礎關鍵設施'''
            if Critical_Infrastructure_Sectors.find("communications") > -1:
                find_industry = True
                logsFunction.appendWrite('產業別是5g基礎關鍵設施')                                                               
                res = ES_ip.search(index = 'sec_info_5g', body = query)
                if res["hits"]["total"] == 0:
                    ES_ip.index(index = 'sec_info_5g', doc_type = "info_5g", id = d["_id"], body = d["_source"])                        

            '''是否為電商基礎關鍵設施'''
            if Critical_Infrastructure_Sectors.find("commercial facilities") > -1:
                find_industry = True
                logsFunction.appendWrite('產業別是電商基礎關鍵設施')                                                               
                res = ES_ip.search(index = 'sec_info_ecommerce', body = query)
                if res["hits"]["total"] == 0:
                    ES_ip.index(index = 'sec_info_ecommerce', doc_type = "info_ecommerce", id = d["_id"], body = d["_source"])                        
        
        except Exception as e:
            logsFunction.appendWrite('寫入api錯誤')
            print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

        if find_industry:
            logsFunction.appendWrite('產業別不屬於定義之類別')
        logsFunction.appendWrite(('-------finish-------'))

def get_NTISAC():
    '''撈取ICS-CERT的時間範圍'''
    filter_time = get_time()
    print('撈出ICS_Cert資料...')

    '''撈取ICS-CERT資料 '''
    get_ICSCert_data(filter_time)
    print('完成')

@click.command()
@click.option('--es_ip', type=str,default='211.23.163.51:59200')
@click.option('--sched_period', type=float,default=30)#單位為分鐘
def run(es_ip, sched_period):
    global ES_ip    
    ES_ip = Elasticsearch(es_ip)   
    if not ES_ip.indices.exists(index = 'sec_info_gov'):
        ES_ip.indices.create(index = 'sec_info_gov')
    if not ES_ip.indices.exists(index = 'sec_info_finance'):
        ES_ip.indices.create(index = 'sec_info_finance')
    if not ES_ip.indices.exists(index = 'sec_info_5g'):
        ES_ip.indices.create(index = 'sec_info_5g')
    if not ES_ip.indices.exists(index = 'sec_info_ecommerce'):
        ES_ip.indices.create(index = 'sec_info_ecommerce')
    '''log紀錄執行狀況'''
    global logsFunction
    logsFunction = LogsFunc("NTISAC")
    schedule.every(sched_period).minutes.do(get_NTISAC)
    schedule.run_all()  # 即時執行

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    run()
