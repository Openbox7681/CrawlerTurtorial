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


def get_detail(url_detail, result_json):
    response = requests.get(url_detail)
    soup_detail = BeautifulSoup(response.text, 'lxml')
    text_body = soup_detail.find("div",{"id" : "story_body_content"}).find_all("p")
    description = ""
    tag_list = list()
    try:
        for item in text_body:
            description = description +  item.text + "\n"
        result_json["Description"] = description
    except Exception as e :
        result_json["Description"] = ""
    try:
        tag_body = soup_detail.find_all("div", {"id":"story_tags"})[0].find_all("a")
        for tag in tag_body:
            tag_list.append(tag.text)
        tag_list = ",".join(tag_list)
        tag_list = tag_list
        #print tag_list
        result_json["Tag"] = tag_list
    except Exception as e:
        result_json["Tag"] = ""
        logsFunction.appendWrite(str(e))
        #print result_json["Tag"]
    try:
        post_time = soup_detail.find("div",{"class" : "story_bady_info_author"}).find("span").text.split(' ')[-2].replace('-', '/', 3)
        # print (post_time)
        result_json["PublishTime"] = post_time
    except Exception as e :
        result_json["PublishTime"] = ""


def get_title(url, index_name):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
    result_list =list()
    soup_body = soup.find_all("div",{"id" : "ranking_body"})[0]
    soup_body = soup_body.find_all("tr")
    try: 
        for txt in soup_body:
            result_json = dict()
            text = txt.find_all("td")
            if len(text) != 0:
                result_json["Title"] = txt.find_all("td")[1].getText()
                URL_detail = txt.find_all("td")[1].find_all("a")[0].get("href")
                result_json["Class"] = txt.find_all("td")[2].getText()
                # result_json["PublishTime"] = txt.find_all("td")[3].getText()
                result_json["Viewing_Count"] = txt.find_all("td")[4].getText()
                result_json["Reference"] = None
                result_json["URL"] = URL + txt.find_all("td")[1].find("a").get("href")
                get_detail(result_json["URL"], result_json)
                id_number = txt.find_all("td")[1].find("a").get("href").split("/")
                id_number = result_json["PublishTime"].replace(" ","_") +"_"+id_number[-1] + "_"+id_number[-2]
                print (id_number)

                create_time_segmentation = result_json["PublishTime"].split("/")
                es_index = "sec_info_udn-" + create_time_segmentation[0] 
                result_json = json.dumps(result_json, ensure_ascii=False)
                try:
                    res = es.index(index=es_index, doc_type='udn', body=result_json, id=id_number)
                    print (res["result"])
                except:
                    print ("Save fail")

                print (res["result"])
                print (txt.find_all("td")[1].getText())
                print ("Crawler data time is " + txt.find_all("td")[3].getText())
    except Exception as e:
        print (str(e))
        logsFunction.appendWrite(str(e))


def month_string_to_number(month):
    m = {
        'Jan': 1,
        'Feb': 2,
        'Mar': 3,
        'Apr': 4,
        'May': 5,
        'Jun': 6,
        'Jul': 7,
        'Aug' : 8,
        'Sep' : 9,
        'Oct' : 10,
        'Nov' : 11,
        'Dec' : 12
            }
    try:
        return m[month]
    except:
        return 0

if __name__ == '__main__': 
    logsFunction = LogsFunc("sec_udn")
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
    index_name = 'sec_info_udn'
    ua = UserAgent()
    headers = {'User-Agent': ua.random}
    ##爬蟲狀況寫入MySQL
    #sqlc = mysql_conn.ConnectMYsql(mysql_username, mysql_password, mysql_host, mysql_port, mysql_database)
    crawlername = 'udn'
    isimmediate = True
    Status = 'RUNNING'
    Pid = os.getpid()
    lastupdatetime = datetime.datetime.now()
    #開始爬蟲
    try:
        time_duration = time_end - time_start
        for i in range(time_duration.days):
            time_end -= datetime.timedelta(days=i)
            nowaday = time_end.strftime("%Y/%m/%d")
            nowaday_year = time_end.strftime("%Y")
            print ("Start crawler time is " + nowaday)
            #index照月份分類
            index_name_y = index_name+"-"+nowaday_year
            index_name_all = index_name + "*"
            # try:
            #     res = es.indices.create(index = index_name_y)
            #     print (res)
            # except Exception as e :
            #     print (str(e))
            #     print ("Index already exists")
            query = {"query":{"match_all":{}}}
            total_res = es.count(index=index_name_all, body=query)
            total =  total_res["count"]
            #sqlc.update(crawlername, isimmediate, Status, Pid, lastupdatetime, total)
            URL = "https://udn.com"
            URL_date = URL + "/news/archive/0/0/" + nowaday
            response = requests.get(URL_date)
            soup = BeautifulSoup(response.text, 'lxml')
            pages_number = soup.find("div",{"class" : "pagelink"}).find("span",{"class":"total"}).getText().split(" ")[-2]
            URL_title = ""
            #照頁碼爬當日的新聞
            for page in range(1, int(pages_number)+1):
                URL_title = URL_date + "/" + str(page)
                print (URL_title)
                get_title(URL_title, index_name_y)
        logsFunction.appendWrite('udn')
        print ("Crawler Finish!!!!")
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
        logsFunction.appendWrite(str(e))
