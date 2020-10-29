# !/usr/bin/python
# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import html.parser
import re
from elasticsearch import Elasticsearch
import datetime
import sys
import logging
import time
import os
from logsContainer import LogsFunc
#import mysql_schema as mysql_conn
import configparser
from fake_useragent import UserAgent
import json


#reload(sys)
#sys.setdefaultencoding('utf-8')






def url_detail_insert(url, class_name, title, index_name):
    #取得內文資訊並寫入ES
    result_dict = dict()
    result_dict["Class"] = class_name
    result_dict["Title"] = title
    
    try:
        result_dict["URL"] =url
        result_dict["Description"] = all_content
        #date = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S+00:00") 
        result_dict["PublishTime"] = t_date.split(" ")[0].replace('-', '/', 3)
        result_dict["Viewing_Count"] = None
        result_dict["Reference"] = None
        result_dict["Tag"] = None
        _id = date.strftime("%Y-%m-%d") +"_"+ url.split("/")[-1]
        
        create_time_segmentation = result_dict["PublishTime"].split("/")
        es_index = "sec_info_yahoo-" + create_time_segmentation[0] 
        result_json = json.dumps(result_dict, ensure_ascii=False)
        try:
            res = es.index(index=es_index, doc_type='yahoo', body=result_json, id=_id)
            print (res["result"])
        except:
            print ("Save fail")

        # print (result_json)
    except Exception as e:
        result_dict = dict()
        print ("The website structure is change, Need to debug")
        print (str(e))
        print ('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))
        error_message = '--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e)
        logsFunction.appendWrite(error_message)
        logsFunction.EsappendWrite(error_message,es, crawlername, "error")
        res = dict()
        res["result"] = "Failed"
    return res["result"]





if __name__ == '__main__': 
    logsFunction = LogsFunc("info_yahoo")
    #Es connect setting
    cf = configparser.ConfigParser()
    cf.read(os.path.abspath(os.path.dirname(os.path.abspath(__file__))) +  "/../crawler_config.ini")
    es_host = cf.get("Elasticsearch", "HOST")
    es_port = cf.get("Elasticsearch", "PORT")
#    mysql_username=cf.get("MYSQL", "mysql_username")
#    mysql_password=cf.get("MYSQL", "mysql_password")
#    mysql_host=cf.get("MYSQL", "mysql_host")
#    mysql_port=cf.get("MYSQL", "mysql_port")
#    mysql_database=cf.get("MYSQL", "mysql_database")
    Es_conn = es_host + ":"+ es_port
    es = Elasticsearch(Es_conn, timeout=600)
    index_name = 'sec_info_yahoo'
    index_name_all = index_name + "*"
    ua = UserAgent()
    crawlername = "yahoo"
    headers = {'User-Agent': ua.random}


    index_name_all = index_name + "*"
    query = {"query":{"match_all":{}}}
    total_res = es.count(index=index_name_all, body=query)
    total =  total_res["count"]

    URL = "https://tw.news.yahoo.com/archive"
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    #url_list, class_list = get_class_url(soup)
    try:
        res = es.indices.create(index = index_name)
        print (res)
    except Exception as e :
        #print str(e)
        print ("Index already exists")
    ##爬蟲狀況寫入MySQL
    #sqlc = mysql_conn.ConnectMYsql(mysql_username, mysql_password, mysql_host, mysql_port, mysql_database)
    crawlername = 'yahoo'
    isimmediate = True
    Status = 'RUNNING'
    Pid = os.getpid()
    lastupdatetime = datetime.datetime.now()
    # print "Start crawler time is " + lastupdatetime.strftime("%Y/%m/%d")
    # sqlc.update(crawlername, isimmediate, Status, Pid, lastupdatetime, total)
    #開始爬蟲
    try:
        newstype=['politics','finance','entertainment','sports','society','world','lifestyle','health','technology']
        for i in newstype:
            t_class=i
            #print t_class
            URL = "https://tw.news.yahoo.com/"+i+"/archive"
            
            response = requests.get(URL)
            soup = BeautifulSoup(response.text, 'html.parser')               
            title_list = soup.find_all("h3", {"class" : "Mb(5px)"})            
            for title in title_list:
                #新聞網址
                try:
                    t_url = "https://tw.news.yahoo.com/archive"+ title.find("a").get("href")
                    #print t_url
                    #新聞標題
                    try:
                        t_title= title.text
                        print  (t_title)
                    except:
                        continue
                    
                    r =requests.get(t_url)          
                    detail =BeautifulSoup(r.text,'html.parser')                    
                    content = detail.find_all("canvas-body Wow(bw) Cl(start) Mb(20px) Lh(1.7) Fz(18px) D(i)")
                    content = detail.find_all("p")
                    all_content=""              
                    for i in content:
                        try:  
                            #內文
                            content_all=i.getText()
                            all_content+=content_all  
                            #print content_all
                        except Exception:
                            continue
                    date=detail.find("time").get("datetime")
                    
                    date = datetime.datetime.strptime(date,"%Y-%m-%dT%H:%M:%S.%fZ")
                    
                    date=date+datetime.timedelta(hours=8)
                    t_date=str(date)                                           
                    
                    print (t_date)
                except:
                        continue    
                result = url_detail_insert(t_url, t_class, t_title,index_name)                                 
                print (result)
                #try:
                #    url = soup.find("a", {"class" : "next page-numbers"}).get("href")
                #    print url
                #except:
                #    url = ""
                #    break
        
        print ("Crawler Finish!!!!")
        logsFunction.appendWrite('yahoo_crawler')
        isimmediate = False
        Status = 'SUCCESS'
        Pid = None
        query = {"query":{"match_all":{}}}
        total_res = es.count(index=index_name_all, body=query)
        total =  total_res["count"]
        #sqlc.update(crawlername, isimmediate, Status, Pid, lastupdatetime, total)
        #sqlc.conn.close()

    except Exception as e:
        print (str(e))
        print (str(e))
        logsFunction.appendWrite(str(e))

