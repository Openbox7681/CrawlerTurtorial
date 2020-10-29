# -*- coding: utf-8 -*-
#!/usr/bin/python
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

    '''起始日期'''
    start_month = '2018/12/14'
    logsFunction.appendWrite('start month: '+str(start_month))
    start_month = datetime.strptime(start_month, '%Y/%m/%d')
    start_month = calendar.timegm(datetime.timetuple(start_month)) * 1000

    '''結束日期，現在月份的最後一天'''
    end_month = t.replace(day = calendar.monthrange(t.year, t.month)[1])
    # end_month=str(2017)+'/'+str(12)
    logsFunction.appendWrite('end month: '+ str(end_month))
    end_month = calendar.timegm(datetime.timetuple(end_month)) * 1000

    # print('start month timestamp: ', start_month)
    # print('end month timestamp: ', end_month)
    return start_month, end_month

'''撈出es的醫療關鍵字'''
def keyword_setting():
    keyword = []
    ''' get keyword in es'''
    query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "match_all": {}
                    }
                ]
            }
        }
    }
    response = ES_ip.search(index="hisac_keyword",doc_type="keywords", scroll='2m', size=300, body=query)
    print('default keywords : ')
    for d in response["hits"]["hits"]:
        print(d["_source"]["keyword"])
    print('----------------')

    '''save in list'''
    response = ES_ip.search(index="hisac_keyword",doc_type="keywords", scroll='2m', size=300, body=query)
    for d in response["hits"]["hits"]:
        keyword.append(str(d["_source"]["keyword"]))
    return keyword

'''撈出es的醫療設備關鍵字'''
def keyword_devices_setting():
    keyword_devices = []
    ''' get keyword in es'''
    query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "match_all": {}
                    }
                ]
            }
        }
    }
    response = ES_ip.search(index="sec_keyword_medical",doc_type="medical", scroll='2m', size=300, body=query)
    print('default keywords : ')
    for d in response["hits"]["hits"]:
        print(d["_source"]["vendor"])
        print(d["_source"]["product"])
    print('----------------')

    '''save in list'''
    response = ES_ip.search(index="sec_keyword_medical",doc_type="medical", scroll='2m', size=300, body=query)
    for d in response["hits"]["hits"]:
        keyword_devices.append([str(d["_source"]["vendor"]), str(d["_source"]["product"])])
    return keyword_devices

'''撈取ICS-CERT資料'''
def get_ICSCert_data(time, keyw, keyw_ds):
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
                         scroll='2m', size=300, body=query)
    print('the count of ICS_CERT data : '+str(len(response["hits"]["hits"])))

    sid = response['_scroll_id']
    scroll_size = response['hits']['total']
    '''save information'''
    analysis(response,keyw, keyw_ds)
    while (scroll_size > 0):
        # print "Scrolling..."
        response = ES_ip.scroll(scroll_id=sid, scroll='2m')
        # Update the scroll ID
        sid = response['_scroll_id']
        # Get the number of results that we returned in the last scroll
        scroll_size = len(response['hits']['hits'])
        # print "scroll size: " + str(scroll_size)
        '''save information'''
        analysis(response,keyw, keyw_ds)

'''整併報告與漏洞細節'''
def analysis(response_,keyw_,keyw_ds_):
    '''取得ICS-CERT報告'''    
    for length in range(0, len(response_["hits"]["hits"])):
        try:
            logsFunction = LogsFunc("HISAC")
            logsFunction.appendWrite((response_["hits"]["hits"][length]["_source"]["url"]))
            print(length, ' : ', response_["hits"]["hits"][length]["_source"]["url"])
            all_data = str(response_["hits"]["hits"][length])
            '''1. 過濾是否為醫療情資 判斷方法：搜尋全文是否有醫療關鍵字'''
            if str(containsAny(keyw_, all_data)) == 'True' and str(containsAnyForDevices(keyw_ds_, all_data)) == 'True':                
                print('medical or not: yes')
                logsFunction.appendWrite('是醫療情資')

                try:
                    d = response_["hits"]["hits"][length]
                    '''2.再撈出漏洞資訊'''

                    '''將millisecond轉換'''
                    try:
                        IncidentDiscoveryTime = datetime.fromtimestamp(int(d["_source"]["publish_date"])/1000).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        IncidentDiscoveryTime=None
                    # print(type(IncidentDiscoveryTime),IncidentDiscoveryTime)
                    try:
                        IncidentReportedTime = datetime.fromtimestamp(int(d["_source"]["publish_date"])/1000).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        IncidentReportedTime=None

                    '''嚴重程度分數使用CVSS V3，需判斷為高、中、低'''
                    ImpactQualification = None
                    try:
                        score = float(
                            str(d["_source"]["CVSS_V3"]))
                        score = int(score)
                        # print(score)
                        if 0<score<4:
                            ImpactQualification=10
                        elif 4<=score<7:
                            ImpactQualification=20
                        elif 7<=score<=10:
                            ImpactQualification=30
                        # print('ImpactQualification', ImpactQualification)
                    except:
                        ImpactQualification = None

                    '''整理描述的欄位內容，分別有：ICS-CERT概述、廠商、設備、利用方式、類型、漏洞描述'''
                    description = 'Overview: \n'+'Vendor: '+d["_source"]["vendor"]+'\n'+'Equipment: '+d["_source"]["equipment"]+'\n'+'Vulnerabilities: '+d["_source"]["vultype"]+'\n'+'\n'+'Description: \n'

                    '''整合多筆漏洞連結'''
                    url=''
                    for detail in d["_source"]["vulnerability_overview"]:
                        cve_detail = get_cve_data(str(detail["CVE_ID"]))
                        # print(detail["CVE_ID"])
                        '''整理描述的欄位內容，再加上漏洞編號、漏洞概述'''
                        description += "["+detail["CVE_ID"]+'] \n'+cve_detail["overview"]+'\n'

                        if len(d["_source"]["cve_id"])==1:
                            url+="https://secbuzzer.co/vulnerability/"+str(cve_detail["CVE_ID"])
                        else:
                            url+="https://secbuzzer.co/vulnerability/"+str(cve_detail["CVE_ID"])+"; "

                    description+='\n'+'Mitigations: \n'+d["_source"]["vendor_mitigation"]+'\n'

                    '''整合多筆漏洞編號'''
                    CVE_ID=''
                    if len(d["_source"]["cve_id"])==1:
                        CVE_ID=d["_source"]["cve_id"][0]
                    else:
                        CVE_ID=d["_source"]["cve_id"][0]+"..."

                    '''利用方式(手法研判)'''
                    LeveragedDescription=None
                    try:
                        LeveragedDescription=str(d["_source"]["vultype"])
                    except:
                        LeveragedDescription=None

                    '''產品清單'''
                    AffectedSoftwareDescription=''
                    try:
                        for i in d["_source"]["product"]:
                            AffectedSoftwareDescription+=str(i)+'\n'
                    except:
                        AffectedSoftwareDescription=None

                    featureJson = {
                            "Id": None,
                            "SourceCode": "SEC",
                            "StixTitle": "OTH",
                            "IncidentId": CVE_ID,
                            "IncidentTitle": d["_source"]["title"],
                            "IncidentDiscoveryTime": IncidentDiscoveryTime,
                            "IncidentReportedTime": IncidentReportedTime,
                            "IncidentClosedTime": None,
                            "Description": description,
                            "Category": "None",
                            "ReporterName": "SecBuzzer",
                            "ReporterNameUrl": "https://secbuzzer.co/",
                            "ResponderPartyName": None,
                            "ResponderContactNumbers": None,
                            "ResponderElectronicAddressIdentifiers": None,
                            "ImpactQualification": ImpactQualification,
                            "CoaDescription": d["_source"]["vendor_mitigation"],
                            "Confidence": None,
                            "Reference": url,
                            "ObservableIpAddress": None,
                            "SocketIpAddress": None,
                            "SocketPort": None,
                            "SocketProtocol": None,
                            "CustomIpAddress": None,
                            "CustomPort": None,
                            "CustomProtocol": None,
                            "DestinationIpAddress": None,
                            "DestinationPort": None,
                            "DestinationProtocol": None,
                            "LeveragedDescription": LeveragedDescription,
                            "AffectedSoftwareDescription": AffectedSoftwareDescription,
                            "ResourcesSourceIpAddress": None,
                            "ResourcesDestinationPort": None,
                            "ResourcesDestinationProtocol": None,
                            "ResourcesDestination": None,
                            "ScanEngine": None,
                            "ScanVersion": None,
                            "ScanResult": None,
                            "RelatedIncidentId": "None",
                            "RelatedIncidentTimestamp": None,
                            "PublicInformationNo": None
                        }
                    # print(json.dumps(featureJson, indent=2))

                    '''api test sever:  http://211.23.163.52:8080/open/api/sec_isac'''
                    '''api real sever:  https://hisac.nat.gov.tw/open/api/sec_isac'''

                    test_api_url = 'http://211.23.163.52:8081/open/api/sec_isac'
                    real_api_url = 'https://hisac.nat.gov.tw/open/api/sec_isac'
                    #message_to_log1=(post_to_api(test_api_url, featureJson))
                    #message_to_log2=(post_to_api(real_api_url, featureJson))
                    query = {
                        "query": {
                            "term": {
                                "IncidentId.keyword": featureJson["IncidentId"]
                            }
                        }
                    }
                    res = ES_ip.search(index = ES_index, body = query)
                    if res["hits"]["total"] == 0:
                        ES_ip.index(index = ES_index, doc_type = "info_medical", id = featureJson["IncidentId"], body = featureJson)

                    '''寫入log檔'''
                    #logsFunction.appendWrite(str('測試機： ')+str(message_to_log1))
                    #logsFunction.appendWrite(str('正式機： ')+str(message_to_log2))
                except Exception as e:
                    print(e)
                    # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))
                    # print(str(detail["CVE_ID"])+'  not in es index')
                    logsFunction.appendWrite(str(detail["CVE_ID"])+' 沒有在es')
            else:
                print('medical or not: no')
                logsFunction.appendWrite('不是醫療情資')
        except Exception as e:
            print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))
            print('insert error')        
        logsFunction.appendWrite(('-------finish-------'))

'''在全文中搜尋關鍵字'''
def containsAny(seq, aset):
    ''' Check whether sequence seq contains ANY of the items in aset. '''   
    for c in seq:
        if c in aset:            
            return True
    return False

'''在全文中搜尋醫療設備'''
def containsAnyForDevices(seq, aset):
    ''' Check whether sequence seq contains ANY of the items in aset. '''        
    for c in seq:                               
        if ' ' + c[0] + ' ' in aset and ' ' + c[1] + ' ' in aset:            
            return True
    return False

def get_cve_data(cve):
    ''' 從漏洞資料庫中，抓取漏洞資訊 '''
    # print(cve)
    query = {
        "query": {
            "term": {
                "CVE_ID.keyword": ""+str(cve)+""
            }
        }
    }
    response = ES_ip.search(index="sec_nvd-*",body=query)
    # print(response["hits"]["hits"])
    return response["hits"]["hits"][0]["_source"]

'''透過api傳送資料'''
def post_to_api(url_, data):
    response = requests.post(url=url_, json=data)
    pastebin_url = response.text
    # print("The pastebin URL is:%s" % pastebin_url)
    return pastebin_url


def get_HISAC():
    '''撈取ICS-CERT的時間範圍'''
    filter_time = get_time()

    '''撈取es醫療關鍵字 '''
    keywords = keyword_setting()
    # print(keywords)
    '''醫療設備關鍵字 '''
    keywords_devices = keyword_devices_setting()         

    print('撈出ICS_Cert資料...')

    '''撈取ICS-CERT資料 '''
    get_ICSCert_data(filter_time, keywords, keywords_devices)
    # print('total get '+str(len(CVE_List))+' ICS_Cert data')

@click.command()
@click.option('--es_ip', type=str,default='211.23.163.51:59200')
@click.option('--es_index', type=str,default='sec_info_medical')
@click.option('--sched_period', type=float,default=30)#單位為分鐘
def run(es_ip, es_index, sched_period):
    global ES_ip
    global ES_index
    ES_ip = Elasticsearch(es_ip)
    ES_index = es_index
    if not ES_ip.indices.exists(index = ES_index):
        ES_ip.indices.create(index = ES_index)
    '''log紀錄執行狀況'''
    global logsFunction
    logsFunction = LogsFunc("HISAC")
    schedule.every(sched_period).minutes.do(get_HISAC)
    schedule.run_all()  # 即時執行


    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    run()
