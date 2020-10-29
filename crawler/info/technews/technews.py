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
 


#Es connect setting
cf = configparser.ConfigParser()
cf.read(os.path.abspath(os.path.dirname(os.path.abspath(__file__))) +  "/../crawler_config.ini")
es_host = cf.get("Elasticsearch", "HOST")
es_port = cf.get("Elasticsearch", "PORT")
#mysql_username=cf.get("MYSQL", "mysql_username")
#mysql_password=cf.get("MYSQL", "mysql_password")
#mysql_host=cf.get("MYSQL", "mysql_host")
#mysql_port=cf.get("MYSQL", "mysql_port")
#mysql_database=cf.get("MYSQL", "mysql_database")
Es_conn = es_host + ":"+ es_port
crawlername = "technews"
es = Elasticsearch(Es_conn, timeout=600)


def get_detail(url_detail):
    result_json = dict()
    print (url_detail)
    response = requests.get(url_detail)
    soup = BeautifulSoup(response.text, 'lxml')
    
    ClassList = list()
    for Class in soup.find("header", {"class" : "entry-header"}).findAll("span")[5].find_all("a"):
        ClassList.append(Class.getText())
        
    Publish_Time = soup.find("header", {"class" : "entry-header"}).findAll("span")[3].text.split()
    PublishTime = Publish_Time[0] +"-"+ Publish_Time[2] +"-"+ Publish_Time[4]
    
    Description = ""
    for content in soup.find("div", {"class" : "indent"}).find_all("p"):
        Description += content.text + '\n'
    
    try:
        result_json["Title"] = soup.find("h1", {"class" : "entry-title"}).text
    except:
        result_json["Title"] = ""
    try:
        result_json["Class"] = ClassList
    except:
        result_json["Class"] = ""
    try:
        result_json["PublishTime"] = PublishTime.replace('-', '/', 3)
    except:
        result_json["PublishTime"] = ""
    try:
        result_json["URL"] = url_detail
    except:
        result_json["URL"] = ""
    try:
        result_json["Description"] = Description
    except:
        result_json["Description"] = ""
    # try:
    #     result_json["Author"] = soup.find("header", {"class" : "entry-header"}).findAll("span")[1].find("a").text
    # except:
    #     result_json["Author"] = ""
    try:
        URL_FB = "https:" + soup.find("header", {"class" : "entry-header"}).findAll("span")[-1].find("iframe").get("data-src")
        response_fb = requests.get(URL_FB)
        soup_fb = BeautifulSoup(response_fb.text, 'lxml')
        result_json["Viewing_Count"] = soup_fb.find("button").findAll("span")[-1].text
    except:
        result_json["Viewing_Count"] = ""
    result_json["Reference"] = None
    result_json["Tag"] = None

#     print result_json["Title"]
#     print result_json["Class"]
#     print result_json["PublishTime"]
#     print result_json["Description"]
#     print result_json["Author"]
#     print result_json["Viewing_Count"]
    index_name = "info_technews_" + Publish_Time[0] + '.' + Publish_Time[2]
    id_number = Publish_Time[2] + "_" + Publish_Time[4] + "_" + url_detail.split('/')[-2]
    print ("index_name : " + index_name)
    print ("id_number : " + id_number)
    
    create_time_segmentation = result_json["PublishTime"].split("/")
    es_index = "sec_info_technews-" + create_time_segmentation[0] 
    result_json = json.dumps(result_json, ensure_ascii=False)
    try:
        res = es.index(index=es_index, doc_type='technews', body=result_json, id=id_number)
        print (res["result"])
    except:
        print ("Save fail")
    
if __name__ == "__main__":
    logsFunction = LogsFunc("sec_technews")
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
    #開始爬蟲
    try:   
        print (str(time_end) + " to " + str(time_start))
        time_duration =  time_end - time_start
        print (time_duration)
        for i in range(time_duration.days):
            time_end -= datetime.timedelta(days=1)
            date_start = str(time_start.strftime("%Y-%m-%d")).split("-")
            date_end = str(time_end.strftime("%Y-%m-%d")).split("-")
            URL = "https://technews.tw/"
            URL_Date = URL + date_end[0] + '/' + date_end[1] + '/' + date_end[2]
            url_page = []
            url_page.append(URL_Date)
            for j in range (1, 1000):
                URL_Date_Page = URL_Date + '/page/' + str(j)
                response = requests.get(URL_Date_Page)
                soup = BeautifulSoup(response.text, 'lxml')
                try:
                    response_page = requests.get(URL_Date_Page)
                    soup_page = BeautifulSoup(response_page.text, 'lxml')
                    articles = soup.find("div", {"id" : "content"}).find_all("article")
                    
                    for article in articles:
                        print (article.find("a").get("href"))
                        get_detail(article.find("a").get("href"))
                except:
                    print ("change date~")
                    break
        print ("Crawler Finish!!!!")
    except Exception as e:
        print (str(e))
        logsFunction.appendWrite(str(e))
