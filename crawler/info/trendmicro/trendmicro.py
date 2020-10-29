# !/usr/bin/python
# coding:utf-8
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



def url_detail_insert(url, class_name, title, index_name):
    #取得內文資訊並寫入ES
    result_dict = dict()
    result_dict["Class"] = class_name
    result_dict["Title"] = title
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
    try:
        time = soup.find("time" , {"class":"entry-date published"}).get("datetime")
        time_type = datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S+08:00")
        times = time.split("T")[-2].split('/')[-1].replace('-', '/', 3)
        # index_name_m = index_name + "_" +time_type.strftime("%Y.%m")
        _id = time_type.strftime("%Y-%m-%d") +"_"+ url.split("/")[-1]
        result_dict["PublishTime"] = times
        print ("Data published Time" , result_dict["PublishTime"])
        description = soup.find("div", {"class" : "entry-content"})
        reference = description.find_all("p")[-1]
        result_dict["Description"] = description.getText()
        result_dict["Reference"] = reference.getText()
        result_dict["URL"] = url

        create_time_segmentation = result_dict["PublishTime"].split("/")
        es_index = "sec_info_trendmicro-" + create_time_segmentation[0] 
        result_json = json.dumps(result_dict, ensure_ascii=False)
        try:
            res = es.index(index=es_index, doc_type='trendmicro', body=result_json, id=_id)
            print (res["result"])
        except:
            print ("Save fail")

    except Exception as e:
        result_dict = dict()
        print ("The website structure is change, Need to debug")
        print (str(e))
        print ('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))
        error_message = '--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e)
        logsFunction.appendWrite(error_message)
        res = dict()
        res["result"] = "Failed"
    return res["result"]


def get_class_url(sp):
    #取得資料種類及url
    url_list = list()
    class_list = list()
    soup_class = sp.find_all("li" , {"id" : re.compile("menu-item.*")})
    for item in soup_class:
        class_url = item.find("a").get("href")
        class_title = item.find("a").getText()
        #print class_title
        if "blog" in class_url:
            url_list.append(class_url)
            class_list.append(class_title.replace(" ",""))
    return url_list, class_list


if __name__ == '__main__': 
    logsFunction = LogsFunc("info_trendmicro")
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
    if len(sys.argv) == 1:
        time_end = datetime.datetime.now()- datetime.timedelta(days=1)
        #time_end = datetime.strptime(time_end, "%Y%m%d") 
        time_start = time_end - datetime.timedelta(days=7)
        #time_start = datetime.strptime(time_start, "%Y%m%d")
    else:
        time_start = sys.argv[1]
        time_start = datetime.datetime.strptime(time_start, "%Y%m%d")
        time_end = sys.argv[2]
        time_end = datetime.datetime.strptime(time_end, "%Y%m%d")  
    index_name = 'sec_info_trendmicro'
    index_name_all = index_name + "*"
    ua = UserAgent()
    headers = {'User-Agent': ua.random}

    time_duration = time_end - time_start
    for i in range(time_duration.days):
        time_end -= datetime.timedelta(days=i)
        nowaday = time_end.strftime("%Y/%m/%d")
        nowaday_month = time_end.strftime("%Y%m")
        # print ("Start crawler time is " + nowaday)
        #index照月份分類
        index_name_m = index_name+"-"+nowaday_month
        index_name_all = index_name + "*"
    query = {"query":{"match_all":{}}}
    total_res = es.count(index=index_name_all, body=query)
    total =  total_res["count"]

    URL = "https://blog.trendmicro.com.tw/"
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, 'lxml')
    url_list, class_list = get_class_url(soup)
    try:
        res = es.indices.create(index = index_name_m)
        print (res)
    except Exception as e :
        #print str(e)
        print ("Index already exists")
    ##爬蟲狀況寫入MySQL
    #sqlc = mysql_conn.ConnectMYsql(mysql_username, mysql_password, mysql_host, mysql_port, mysql_database)
    crawlername = 'trendmicro'
    isimmediate = True
    Status = 'RUNNING'
    Pid = os.getpid()
    lastupdatetime = datetime.datetime.now()
    print ("Start crawler time is " + lastupdatetime.strftime("%Y/%m/%d"))
    #sqlc.update(crawlername, isimmediate, Status, Pid, lastupdatetime, total)
    #開始爬蟲
    try:
        URL = "https://blog.trendmicro.com.tw/"
        response = requests.get(URL)
        soup = BeautifulSoup(response.text, 'lxml')
        #取出所有種類的列表
        url_list, class_list = get_class_url(soup)
        for i in range(len(url_list)):
            url = url_list[i]
            class_name = class_list[i]
            print ("title url",url)
            while True:
                response = requests.get(url)
                soup = BeautifulSoup(response.text, 'lxml')
                title_list = soup.find_all("h2", {"class" : "entry-title"})
                for title in title_list:
                    t_url =  title.find("a").get("href")
                    t_title = title.find("a").getText()
                    t_class = class_name
                    #print t_url
                    result = url_detail_insert(t_url, t_class, t_title,index_name_m)
                    print (t_title)
                    print (result)
                try:
                    url = soup.find("a", {"class" : "next page-numbers"}).get("href")
                    print (url)
                except:
                    url = ""
                    break
        print ("Crawler Finish!!!!")
        Status = 'SUCCESS'
        logsFunction.appendWrite("info_trendmicro")
    except Exception as e:
        print (str(e))
        print ('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))
        error_message = '--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e)
        logsFunction.appendWrite(error_message)
        print ("Crawler Failed!!!!")
        Status = 'FAILED'
    isimmediate = False
    Pid = None
    query = {"query":{"match_all":{}}}
    total_res = es.count(index=index_name_all, body=query)
    total =  total_res["count"]
    #sqlc.update(crawlername, isimmediate, Status, Pid, lastupdatetime, total)
    #sqlc.conn.close()
