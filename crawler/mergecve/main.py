# -*- coding: utf-8 -*-
#!/usr/bin/python
import json
from elasticsearch import Elasticsearch
from datetime import datetime
from dateutil.relativedelta import *
import time
import calendar
import sys

import click
import schedule

from logContainer import LogsFunc

'''從es中撈出cvedetails資料'''
def get_cvedetail(CVE_ID):
    try:
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "query_string": {
                                "default_field": "cvedetails.CVE_ID.keyword",
                                "query":  "CVE_ID:\"" + str(CVE_ID) + "\""
                            }
                        }
                    ]
                }
            }
        }
        response = ES_ip.search(index="sec_cvedetails-*", body=query)
        if len(response["hits"]["hits"]) > 0:
            return (response)
    except:
        return False

'''從es中撈出NVD資料'''
def get_cveNVD(CVE_ID):
    try:
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "query_string": {
                                "default_field": "nvd.CVE_ID.keyword",
                                "query": "CVE_ID:\"" + str(CVE_ID) + "\""
                            }
                        }
                    ]
                }
            }
        }
        response = ES_ip.search(index="sec_nvd-*", body=query)
        if len(response["hits"]["hits"]) > 0:
            return (response)
    except:
        return False

'''從es中撈出vuldb資料'''
def get_cvevuldb(CVE_ID):
    try:
        query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "query_string": {
                                "default_field": "vuldb.CVE_ID",
                                "query": "CVE_ID:\"" + str(CVE_ID) + "\""
                            }
                        }
                    ]
                }
            }
        }
        response = ES_ip.search(index="sec_vuldb-*", body=query)
        if len(response["hits"]["hits"]) > 0:
            return (response)
    except:
        return False

'''從es中撈出exploitdb資料'''
def get_exploitdb(CVE_ID):
    try:
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "query_string": {
                                "default_field": "exploit.cve_id",
                                "query": "cve_id:\"" + str(CVE_ID) + "\""
                            }
                        }
                    ]
                }
            }
        }
        response = ES_ip.search(index="sec_exploitdb-*", body=query)
        if len(response["hits"]["hits"]) > 0:
            return (response)
    except:
        return False

'''從es中撈出0daytoday資料'''
def get_0daytoday(CVE_ID):
    try:
        query = {
             "query": {
                "bool": {
                    "must": [
                        {
                            "query_string": {
                                "default_field": "exploit.cve_id.keyword",
                                "query": "exploit.cve_id:\"" + str(CVE_ID) + "\""
                            }
                        }
                    ]
                }
            }
        }
        response = ES_ip.search(index="sec_0daytoday-*", body=query)
        if len(response["hits"]["hits"]) > 0:
            return (response)
    except:
        return False

'''合併cve資訊，打進mergecve es'''
def get_features(match,esname):
    for i in match:
        '''取得 cvedetails資料'''
        a = get_cvedetail(i)
        '''取得 NVD資料'''
        b = get_cveNVD(i)
        '''取得 vuldb資料'''
        c = get_cvevuldb(i)
        '''取得 exploitdb資料'''
        e = get_exploitdb(i)
        '''取得 0daytoday資料'''
        f=get_0daytoday(i)
                
        '''有些cve審核未通過，不新增，使用DO NOT USE THIS CANDIDATE來判斷'''
        try:
            if (str(b["hits"]["hits"][0]["_source"]["overview"]).find("DO NOT USE THIS CANDIDATE")) > -1:
                print('!!!DO NOT USE THIS CANDIDATE!!!')

            featureJson={}
            
            featureJson["title"] = str(i)
            featureJson["cve_id"] = str(i)

            '''cvedetails資訊'''
            featureJson["cvedetails_url"] = None
            featureJson["product_number"] = 0
            featureJson["vendor_number"] = 0
            featureJson["product"] = None
            featureJson["vendor"] = None
            featureJson["product_list"] = None
            featureJson["product_list_count"] = None
            featureJson["vultype"] = None

            try:
                for d in a["hits"]["hits"]:

                    # 影響產品清單(unique)
                    products = set()
                    for p in d["_source"]["Products_Affected"]:
                        products.add(p["product"])

                    # 影響廠商清單(unique)
                    vendors = set()
                    for v in d["_source"]["Products_Affected"]:
                        vendors.add(p["vendor"])

                    # add to featureJson
                    featureJson["cvedetails_url"] = (d["_source"]["url"])
                    featureJson["product_number"] = len(products)
                    featureJson["vendor_number"] = len(vendors)
                    if len(products) == 0:
                        products = None
                    else:
                        featureJson["product"] = list(products)
                    if len(vendors) == 0:
                        vendors = None
                    else:
                        featureJson["vendor"] = list(vendors)
                    featureJson["product_list"] = d["_source"]["Products_Affected"]
                    featureJson["product_list_count"] = len(d["_source"]["Products_Affected"])#算數量
                    featureJson["vultype"] = (d["_source"]["vultype"])

            except Exception as ex:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(ex))
                # print(i, 'not in cvedetail')
            
            '''NVD資訊'''
            featureJson["CVSS_V2_access_complexity"] = None
            featureJson["CVSS_V2_access_vector"] = None
            featureJson["CVSS_V2_authentication"] = None
            featureJson["CVSS_V2_base_score"] = None
            featureJson["CVSS_V2_exploitability_subscore"] = None
            featureJson["CVSS_V2_impact_subscore"] = None
            featureJson["CVSS_V2_integrity"] = None
            featureJson["CVSS_V2_availability"] = None
            featureJson["CVSS_V2_impact_type"] = None
            featureJson["CVSS_V2_confidentiality"] = None

            featureJson["CVSS_V3_attack_complexity"] = None
            featureJson["CVSS_V3_attack_vector"] = None
            featureJson["CVSS_V3_availability"] = None
            featureJson["CVSS_V3_base_score"] = None
            featureJson["CVSS_V3_confidentiality"] = None
            featureJson["CVSS_V3_exploitability_score"] = None
            featureJson["CVSS_V3_impact_score"] = None
            featureJson["CVSS_V3_integrity"] = None
            featureJson["CVSS_V3_privileges_required"] = None
            featureJson["CVSS_V3_scope"] = None
            featureJson["CVSS_V3_user_interaction"] = None

            featureJson["NVD_url"] = None
            featureJson["cwe_id"] = None
            featureJson["NVD_References"] = None
            featureJson["NVD_References_count"] = None
            featureJson["content"] = None
            featureJson["update_date"] = None
            featureJson["publish_date"] = None
            featureJson["cve_created_date"] = None
            featureJson["patch_date"] = None

            try:
                for d in b["hits"]["hits"]:
                    # add to featureJson
                    featureJson["CVSS_V2_access_complexity"] = (
                        d["_source"]["CVSS_v2_Access_Complexity"])
                    featureJson["CVSS_V2_access_vector"] = (
                        d["_source"]["CVSS_v2_Access_Vector"])
                    featureJson["CVSS_V2_authentication"] = (
                        d["_source"]["CVSS_v2_Authentication"])
                    featureJson["CVSS_V2_base_score"] = (
                        d["_source"]["CVSS_v2_Base_Score"])
                    featureJson["CVSS_V2_exploitability_subscore"] = (
                        d["_source"]["CVSS_v2_Exploitability_Subscore"])
                    featureJson["CVSS_V2_impact_subscore"] = (
                        d["_source"]["CVSS_v2_Impact_Subscore"])
                    featureJson["CVSS_V2_integrity"] = (
                        d["_source"]["CVSS_v2_Integrity"])
                    featureJson["CVSS_V2_availability"] = (
                        d["_source"]["CVSS_v2_Availability"])
                    featureJson["CVSS_V2_impact_type"] = (
                        d["_source"]["CVSS_v2_Impact_Type"])
                    featureJson["CVSS_V2_confidentiality"] = (
                        d["_source"]["CVSS_v2_Confidentiality"])

                    featureJson["CVSS_V3_attack_complexity"] = (
                        d["_source"]["CVSS_v3_Attack_Complexity"])
                    featureJson["CVSS_V3_attack_vector"] = (
                        d["_source"]["CVSS_v3_Attack_Vector"])
                    featureJson["CVSS_V3_availability"] = (
                        d["_source"]["CVSS_v3_Availability"])
                    featureJson["CVSS_V3_base_score"] = (
                        d["_source"]["CVSS_v3_Base_Score"])
                    featureJson["CVSS_V3_confidentiality"] = (
                        d["_source"]["CVSS_v3_Confidentiality"])
                    featureJson["CVSS_V3_exploitability_score"] = (
                        d["_source"]["CVSS_v3_Exploitability_Score"])
                    featureJson["CVSS_V3_impact_score"] = (
                        d["_source"]["CVSS_v3_Impact_Score"])
                    featureJson["CVSS_V3_integrity"] = (
                        d["_source"]["CVSS_v3_Integrity"])
                    featureJson["CVSS_V3_privileges_required"] = (
                        d["_source"]["CVSS_v3_Privileges_Required"])
                    featureJson["CVSS_V3_scope"] = (
                        d["_source"]["CVSS_v3_Scope"])
                    featureJson["CVSS_V3_user_interaction"] = (
                        d["_source"]["CVSS_v3_User_Interaction"])
                    featureJson["NVD_url"] = (d["_source"]["url"])
                    featureJson["cwe_id"] = (d["_source"]["CWE"])
                    featureJson["NVD_References"] = (
                        d["_source"]["References"])
                    featureJson["NVD_References_count"] = len(
                        d["_source"]["References"])
                    featureJson["content"] = (d["_source"]["overview"])
                    featureJson["update_date"] = (
                        d["_source"]["update_date"])
                    featureJson["publish_date"] = (
                        d["_source"]["publish_date"])
                    featureJson["cve_created_date"] = (
                        d["_source"]["date_entry_created"])
                    featureJson["patch_date"] = (
                        d["_source"]["patch_date"])

            except:
                pass
                # print(i, 'not in NVD')
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            '''vuldb資訊'''
            try:
                featureJson["vuldb_url"] = None
                featureJson["today_price"] = None
                featureJson["zeroday_price"] = None
                for d in c["hits"]["hits"]:
                    try:
                        featureJson["vuldb_url"] = (d["_source"]["url"])
                    except:
                        featureJson["vuldb_url"] = None
                    '''get today price from es'''
                    try:    
                        today_price = (d["_source"]["today_price"])
                        featureJson["today_price"] = (
                            today_price[len(today_price)-1])  # get last price
                    except:
                        featureJson["today_price"] = None
                    '''get zeroday price from es'''
                    try:
                        featureJson["zeroday_price"] = (
                            d["_source"]["zeroday_price"][0])  
                    except:
                        featureJson["zeroday_price"] = None
            except Exception as ex:
                pass
                # print '--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(ex)
                # print(i, 'not in vuldb')

            '''exploitdb資訊:先從exploit找，如果沒有再去0day找'''
            try:
                featureJson["EDB_ID"] = None
                featureJson["EDB_title"] = None
                featureJson["EDB_author"] = None
                featureJson["EDB_download_url"] = None
                featureJson["EDB_web_url"] = None
                featureJson["EDB_platform"] = None
                featureJson["EDB_type"] = None
                featureJson["exploit"] = 0
                featureJson["exploit_date"] = None
                featureJson["exploit_code"] = None
                featureJson["exploit_code_html"] = None
                featureJson["EDB_related_CVE"] = None
                for d in e["hits"]["hits"]:
                    featureJson["EDB_ID"] = (d["_source"]["EDB_ID"])
                    featureJson["EDB_title"] = (d["_source"]["title"])
                    featureJson["EDB_author"] = (d["_source"]["author"])
                    featureJson["EDB_download_url"] = (d["_source"]["download_url"])
                    featureJson["EDB_web_url"] = (d["_source"]["web_url"])
                    featureJson["EDB_platform"] = (d["_source"]["platform"])
                    featureJson["EDB_type"] = (d["_source"]["vultype"])
                    featureJson["exploit"] = int(1)
                    featureJson["exploit_date"] = (d["_source"]["publish_date"])
                    featureJson["exploit_code"] = (d["_source"]["exploit_code"])
                    featureJson["exploit_code_html"] = (d["_source"]["exploit_code_html"])
                    if len((d["_source"]["cve_id"]))>1:
                        featureJson["EDB_related_CVE"] = (d["_source"]["cve_id"])
            except:
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))
                try:
                    for d in f["hits"]["hits"]:
                        featureJson["EDB_ID"] = (d["_id"])
                        featureJson["EDB_title"] = (d["_source"]["exploit"]["title"])
                        featureJson["EDB_author"] = (d["_source"]["exploit"]["author"])
                        featureJson["EDB_download_url"] = None
                        featureJson["EDB_web_url"] = (d["_source"]["exploit"]["web_url"])
                        featureJson["EDB_platform"] = (d["_source"]["exploit"]["platform"])
                        featureJson["EDB_type"] = (d["_source"]["exploit"]["type"])
                        featureJson["exploit"] = int(1)
                        featureJson["exploit_date"] = (d["_source"]["publish_date"])
                        featureJson["exploit_code"] = (d["_source"]["exploit"]["raw"])
                        featureJson["exploit_code_html"] = None
                        featureJson["EDB_related_CVE"] = None

                except:
                    featureJson["EDB_ID"] = None
                    featureJson["EDB_title"] = None
                    featureJson["EDB_author"] = None
                    featureJson["EDB_download_url"] = None
                    featureJson["EDB_web_url"] = None
                    featureJson["EDB_platform"] = None
                    featureJson["EDB_type"] = None
                    featureJson["exploit"] = 0
                    featureJson["exploit_date"] = None
                    featureJson["exploit_code"] = None
                    featureJson["exploit_code_html"] = None
                    featureJson["EDB_related_CVE"] = None
                    # print('not in exploitdb')
                    # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))


            '''tweet/retweet數量資訊'''
            tweet_count = 0
            retweet_count = 0
            try:
                query ={
                    "query": {
                        "bool": {
                        "must": [
                            {
                            "query_string": {
                                "default_field": "text.keyword",
                                "query": "text:\"" + str(i) + "\""
                            }
                            },
                            {
                            "query_string": {
                                "default_field": "extended_tweet.full_text.keyword",
                                "query": "text:\"" + str(i) + "\""
                            }
                            }
                        ]
                        }
                    }
                }
               
                response2 = ES_ip.search(index="sec_twittercve-*", body=query)
                # print(response2['hits']['total'])
                tweet_count = response2['hits']['total']

            except:
                tweet_count = 0

            try:
                query ={
                    "query": {
                        "bool": {
                        "must": [
                            {
                            "query_string": {
                                "default_field": "text.keyword",
                                "query": "text:\"" + str(i) + "\""
                            }
                            },
                            {
                            "query_string": {
                                "default_field": "extended_tweet.full_text.keyword",
                                "query": "text:\"" + str(i) + "\""
                            }
                            },
                            {
                            "query_string": {
                                "default_field": "text.keyword",
                                "query": "text:'RT'"
                            }
                            },
                            {
                            "query_string": {
                                "default_field": "extended_tweet.full_text.keyword",
                                "query": "text:'RT'"
                            }
                            }
                        ]
                        }
                    }
                }
              
                response2 = ES_ip.search(index='sec_twittercve-*', body=query)
                # print(response2['hits']['total'])
                retweet_count = response2['hits']['total']
            except:
                tweet_count = 0

            featureJson["tweet_count"] = (tweet_count - retweet_count)
            featureJson["retweet_count"] = (retweet_count)
            # print((tweet_count - retweet_count))
            # print((retweet_count))
            
            '''產業類別 industry type資訊'''
            try:
                query ={
                    "query": {
                        "bool": {
                        "must": [
                            {
                            "term": {
                                "cve_id.keyword": str(i)
                            }
                            }
                        ]
                        }
                    }
                }
                #print(esname)
                response2 = ES_ip.search(index=esname, body=query)
                featureJson["industry_types"]=response2["hits"]["hits"][0]["_source"]["industry_types"]
                #print(str(i),'industry_types: ',response2["hits"]["hits"][0]["_source"]["industry_types"])
            except:
                featureJson["industry_types"]=None
                #print('cant find industry types')

            '''0daytoday資訊'''
            featureJson["0day_exploit_raw"] = None
            featureJson["0day_exploit_views"] = None
            featureJson["0day_exploit_comments"] = None
            featureJson["0day_exploit_author"] = None
            featureJson["0day_exploit_rel_releases"] = None
            featureJson["0day_exploit_price"] = None
            featureJson["0day_exploit_type"] = None
            featureJson["0day_exploit_web_url"] = None
            featureJson["0day_exploit_title"] = None
            featureJson["0day_exploit_risk"] = None
            featureJson["0day_exploit_platform"] = None
            featureJson["0day_publish_date"] = None
            
            try:
                for d in f["hits"]["hits"]:
                    # add to featureJson
                    featureJson["0day_exploit_raw"] = ( d["_source"]["exploit"]["raw"])
                    featureJson["0day_exploit_views"] = ( d["_source"]["exploit"]["views"])
                    featureJson["0day_exploit_comments"] = ( d["_source"]["exploit"]["comments"])
                    featureJson["0day_exploit_author"] = ( d["_source"]["exploit"]["author"])
                    featureJson["0day_exploit_rel_releases"] = ( d["_source"]["exploit"]["rel_releases"])
                    featureJson["0day_exploit_price"] = ( d["_source"]["exploit"]["price"])
                    featureJson["0day_exploit_type"] = ( d["_source"]["exploit"]["type"])
                    featureJson["0day_exploit_web_url"] = ( d["_source"]["exploit"]["web_url"])
                    featureJson["0day_exploit_title"] = ( d["_source"]["exploit"]["title"])
                    featureJson["0day_exploit_risk"] = ( d["_source"]["exploit"]["risk"])
                    featureJson["0day_exploit_platform"] = ( d["_source"]["exploit"]["platform"])
                    featureJson["0day_publish_date"] = ( d["_source"]["publish_date"])

            except:
                featureJson["0day_exploit_raw"] = None
                featureJson["0day_exploit_views"] = None
                featureJson["0day_exploit_comments"] = None
                featureJson["0day_exploit_author"] = None
                featureJson["0day_exploit_rel_releases"] = None
                featureJson["0day_exploit_price"] = None
                featureJson["0day_exploit_type"] = None
                featureJson["0day_exploit_web_url"] = None
                featureJson["0day_exploit_title"] = None
                featureJson["0day_exploit_risk"] = None
                featureJson["0day_exploit_platform"] = None
                featureJson["0day_publish_date"] = None

            try:
                # 新增與更新
                response = ES_ip.index(index=esname, doc_type='detail',body=featureJson, id=str(i))
                print('更新CVE_ID' + str(featureJson["cve_id"]))
                print(response["result"])
            except Exception as e:
                print(e.info)
        except:
            pass
            # print('UnicodeEncodeError')

def get_cve_list(year,month):
    # 建立es 的index，依據年份
    esname = "sec_merge_cve-"+str(year)
    try:
        mapping='{"settings": {"index.mapping.ignore_malformed": true}}'
        res = ES_ip.indices.create(index=esname, body=mapping)
    except Exception as e :
        pass

    #月份第一天
    firstDay = str(year)+"/"+str(month)+str("/01")
    #月份最後一天
    lastDay = str(year)+"/"+str(month)+"/"+str(calendar.monthrange(year,month)[1])

    # print(firstDay)
    mapping_time_1 = datetime.strptime(firstDay, '%Y/%m/%d')
    mapping_time_1 = calendar.timegm(datetime.timetuple(mapping_time_1)) * 1000

    # print(lastDay)
    mapping_time_2 = datetime.strptime(lastDay, '%Y/%m/%d')
    mapping_time_2 = calendar.timegm(datetime.timetuple(mapping_time_2)) * 1000
    print('mapping from ', (mapping_time_1),' to ', (mapping_time_2))

    try:
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "range": {
                                "publish_date": {
                                    "gte": mapping_time_1, "lte": mapping_time_2
                                }
                            }
                        }
                    ]
                }
            }
        }
        response = ES_ip.search(index='sec_nvd-'+str(year), scroll='3m', size=300, body=query)
        # print(len(response["hits"]["hits"]))
        total_size = 0
        sid = response['_scroll_id']
        scroll_size = len(response['hits']['hits'])
        total_size += scroll_size
        CVE_list = []

        for d in response["hits"]["hits"]:
            CVE_list.append(d["_source"]["CVE_ID"])
        print("cve_list!!")
        print(CVE_list)
        get_features(CVE_list,esname)

        while (scroll_size > 0):
            # print("Scrolling...")
            total_size += scroll_size
            print("total_size: "+str(total_size))
            response = ES_ip.scroll(scroll_id=sid, scroll='3m')
            # Update the scroll ID
            sid = response['_scroll_id']
            # Get the number of results that we returned in the last scroll
            scroll_size = len(response['hits']['hits'])
            # print "scroll size: " + str(scroll_size)
            CVE_list = []
            for d in response["hits"]["hits"]:
                CVE_list.append(d["_source"]["CVE_ID"])
            get_features(CVE_list,esname)
    except Exception as ex:
        print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(ex))

def getmergecve():

    '''抓現在的時間'''
    global t 
    t = datetime.now()
    print('The time is : ', t)
    global year
    
    monthRange = 6

    for i in range(monthRange):
        startTime = t + relativedelta(months=-i)
        year=startTime.year
        month=startTime.month
        print('start ',str(year),str(month))
        logsFunction.appendWrite('開始更新'+str(year)+'/'+ str(month)+'月的資料')
        get_cve_list(year,month)
        logsFunction.appendWrite(str(year)+'/'+str(month)+'更新完成')

        
@click.command()
@click.option('--es_ip', type=str,default='211.23.163.51')
@click.option('--es_port', type=str, default='59200')
#30分鐘執行一次
def run(es_ip,es_port):
    global ES_ip
    ES_ip = Elasticsearch(es_ip+ ":" + es_port)
    '''log紀錄執行狀況'''
    global logsFunction
    logsFunction = LogsFunc("merge cve")
    getmergecve()
    


if __name__ == '__main__':
    run()