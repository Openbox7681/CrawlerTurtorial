# !/usr/bin/python3
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
    text_body = soup_detail.find("article",{"class" : "main_content"}).find_all('p')
    # print (text_body)
    
    description = ""
    class_list = list()
    tag_list = list()
    try:
        for item in text_body:
         description = description + item.text + "\n"
        result_json["Description"] = description
        # print (result_json["Description"])
        
    except Exception as e :
        result_json["Description"] = ""
        
        
    try:
        class_body = soup_detail.find("div", {"class":"cate_box"}).find_all('a')
        
        for cla in class_body:
            class_list.append(cla.text)
        class_list = ",".join(class_list)
        # print(class_list)
        
        result_json["Class"] = class_list
        # print (result_json["Class"])
    except Exception as e:
        result_json["Class"] = ""
    try:
        tag_body = soup_detail.find("div", {"class":"article_tags"}).find_all('a')
        
        for tag in tag_body:
            tag_list.append(tag.text)
        tag_list = " ".join(tag_list)
        
        result_json["Tag"] = tag_list
#         print result_json["Tag"]
    except Exception as e:
        result_json["Tag"] = ""

#     print result_json
    create_time_segmentation = result_json["PublishTime"].split("/")
    es_index = "sec_info_bnext-" + create_time_segmentation[0] 
    result_json = json.dumps(result_json, ensure_ascii=False)
    try:
        res = es.index(index=es_index, doc_type='bnext', body=result_json)
        print (res["result"])
    except:
        print ("Save fail")




def get_title(url, index_name):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
    result_list =list()
    soup_body = soup.find_all("div",{"class" : "left"})[0]
    soup_bodys = soup_body.find_all("div",{"class" : re.compile("^(item_box item_sty01 div_tab |item_box item_sty02 item_selected)$")})
    

    try: 
        for bodys in soup_bodys :
            result_json = dict()
            soup_title = bodys.find("div",{"class" : ["item_title font_sty02" ,"item_title sitem_title"]}).getText()
            result_json["Title"] = soup_title.strip()
#             print result_json["Title"]
            result_json["PublishTime"] = bodys.find("div",{"class" : "div_td td1"}).getText().replace('-', '/', 3)
#             print result_json["PublishTime"]
            result_json["Viewing_Count"] = None
            result_json["Reference"] = None
            big_URL = bodys.find("div",{"class" : ["item_text_box div_td" ,"item_text_box"]}).find_all("a")[-2]
            result_json["URL"] = big_URL.get("href")
#             print result_json["URL"]
        
            get_detail(result_json["URL"], result_json)

            # result_json = json.dumps(result_json, ensure_ascii=False)
            # res = es.index(index=index_name, doc_type='bnext', body=result_json)
            # print (result_json)

#                 print txt.find_all("td")[1].getText()
#                 print "Crawler data time is " + txt.find_all("td")[3].getText()
    except Exception as e:
        print (str(e))
        
        

if __name__ == '__main__':         
    logsFunction = LogsFunc("sec_bnext")
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
    # if len(sys.argv) == 1:
    #     time_end = datetime.datetime.now()- datetime.timedelta(days=1)
    #     #time_end = datetime.strptime(time_end, "%Y%m%d") 
    #     time_start = time_end - datetime.timedelta(days=7)
    #     #time_start = datetime.strptime(time_start, "%Y%m%d")
    # else:
    #     time_start = sys.argv[1]
    #     time_start = datetime.datetime.strptime(time_start, "%Y%m%d")
    #     time_end = sys.argv[2]
    #     time_end = datetime.datetime.strptime(time_end, "%Y%m%d")    
    index_name = 'sec_info_bnext'
    ua = UserAgent()
    headers = {'User-Agent': ua.random}

    #sqlc = mysql_conn.ConnectMYsql(mysql_username, mysql_password, mysql_host, mysql_port, mysql_database)
    crawlername = 'bnext'
    isimmediate = True
    Status = 'RUNNING'
    Pid = os.getpid()
    lastupdatetime = datetime.datetime.now()
    try:
        
        # try:
        #     res = es.indices.create(index = index_name)
        #     print (res)
        # except Exception as e :
        #     #print str(e)
        #     print ("Index already exists")    
        URL = "https://www.bnext.com.tw"
        response = requests.get(URL)
        soup = BeautifulSoup(response.text, 'lxml')
        

        URL_date = URL + "/categories/"
        category_body = soup.find("li",{"class" : "dropdown-submenu"}).find("ul",{"class" : "dropdown-menu"}).find_all("a")
        URL_title = ""
        for category in category_body :
            category_URL = category.get("href").split("/")[-1]
            URL_title = URL_date + category_URL
            # print  URL_title
            get_title(URL_title, index_name)
        print ("Crawler Finish!!!!")
        logsFunction.appendWrite('bnext_crawler')
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
