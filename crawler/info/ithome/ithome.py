#-*- coding: utf-8 -*-　
# !/usr/bin/python
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
from elasticsearch import Elasticsearch
import os
from logsContainer import LogsFunc
#import mysql_schema as mysql_conn
import configparser
from fake_useragent import UserAgent
import sys

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
es = Elasticsearch(Es_conn, timeout=600)
ua = UserAgent()
headers = {'User-Agent': ua.random}

class IthomeCrawler():
    
    def __init__(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time
    
    # 解析
    def parse(self):
        URL_main = "https://www.ithome.com.tw"
        response = requests.get(URL_main)
        soup = BeautifulSoup(response.text, 'lxml')
        self.get_classList(URL_main, soup)
    
    # 取得分類清單
    def get_classList(self, URL_main, soup):
        soup_bodys = soup.find("div", {"class" : "nav-collapse collapse"}).find("ul", {"class" : "menu nav"})
        class_list = list()
        # 取得每種分類的href        
        for soup_body in soup_bodys.find_all("li", {"class" : "leaf"}): 
            if soup_body.find("a").get("href")[0] == '/':
                class_list.append(URL_main + soup_body.find("a").get("href"))
            else:
                class_list.append(soup_body.find("a").get("href"))
        print (class_list)
        self.get_newsList(URL_main, class_list)
    
    # 從分類清單中一一搜尋，每頁的新聞href
    def get_newsList(self, URL_main, class_list):
        
        #0~2 分別為新聞、產品評測、技術，3~8則以主題將前述文章再做分類
        for list_num in range (0,9) :
            for page in range(0,20000):
                classPaper = class_list[list_num] + "?page=" + str(page)
                print (class_list[list_num], " : " , classPaper)
                response = requests.get(classPaper)
                soup = BeautifulSoup(response.text, 'lxml')
                items = soup.find("section",{"class" : "main-content span9"}).find_all("div", {"class" : "item"})
                overTime = False
                for item in items:
                    postTime = item.find("p", {"class" : "post-at"}).text.strip(' ')
                    checkTime = datetime.strptime(str(postTime),"%Y-%m-%d")
                    if checkTime >= self.end_time and checkTime <= self.start_time:
                        # list_num == 3 為專欄分類
                        if list_num == 3:
                            self.get_article_paper(item, URL_main, postTime)
                        else:    
                            self.get_paper(item, URL_main, postTime)
                    # 超過日期跳出兩層迴圈，換下個分類
                    else:
                        overTime = True
                        break
                if overTime:
                    break
    
    # 取得專欄內容    
    def get_article_paper(self, item, URL_main, postTime):
        result_json = dict()
        item_href = URL_main + item.find_all("p", {"class" : "title"})[0].find("a").get("href")
        print (item_href)
        response = requests.get(item_href)
        soup = BeautifulSoup(response.text, 'lxml')
        soup_body = soup.find("section", {"class" : "main-content span9"})
        try:
            result_json["PublishTime"] = postTime.replace('-', '/', 3)
        except:
            result_json["PublishTime"] = ''
        try:
            result_json["Title"] = soup_body.find("h1").text
        except:
            result_json["Title"] = ''
        try:
            result_json["Class"] = "專欄"
        except:
            result_json["Class"] = ''     
        try:
            result_json["URL"] = item_href 
        except:
            result_json["URL"] = ''
        try:
            result_json["Description"] = soup_body.find("p").text
        except:
            result_json["Description"] = ''
        result_json["Tag"] = None
        result_json["Reference"] = None
        
        date = datetime.strptime(postTime.strip(' ') ,'%Y-%m-%d')
        index_name = "sec_info_ithome-" + date.strftime('%Y')
        id = date.strftime('%m') + '_' + date.strftime('%d') + '_' + item_href.split('/')[-1]
        result_json = json.dumps(result_json, ensure_ascii=False)
        try:
            res = es.index(index=index_name, doc_type='iThome', body=result_json, id=id)
            print (res["result"])
        except:
            print ("Save fail")
    
    # 取得新聞內容
    def get_paper(self, item, URL_main, postTime):
        result_json = dict()
        item_href = URL_main + item.find_all("p", {"class" : "title"})[0].find("a").get("href")
        print (item_href)
        response = requests.get(item_href)
        soup = BeautifulSoup(response.text, 'lxml')
        try:
            result_json["PublishTime"] = postTime.replace('-', '/', 3)
        except:
            result_json["PublishTime"] = ''
        try:
            result_json["Title"] = soup.find("h1", {"class" : "page-header"}).text
        except:
            result_json["Title"] = ''
        try:
            result_json["Class"] = soup.find("div", {"class" : "category-label"}).text.strip('\n')
        except:
            result_json["Class"] = ''
        try:
            result_json["URL"] = item_href 
        except:
            result_json["URL"] = ''
        # try:
        #     result_json["Summery"] = soup.find("div", {"class" : "content-summary"}).text.strip('\n')
        # except:
        #     result_json["Summery"] = ''
        try:
            result_json["Description"] = soup.find("div", {"class" : "content"}).find("div", {"class" : "field field-name-body field-type-text-with-summary field-label-hidden"}).text
        except:
            result_json["Description"] = ''
        # print (result_json["PublishTime"])
        print (result_json["Title"])
        # print (json.dumps(result_json["Class"], ensure_ascii=False))
        print (result_json["Class"])

        
#         print json.dumps(result_json, ensure_ascii=False)
        date = datetime.strptime(postTime.strip(' ') ,'%Y-%m-%d')
        index_name = "sec_info_ithome-" + date.strftime('%Y') 
        id = date.strftime('%m') + '_' + date.strftime('%d') + '_' + item_href.split('/')[-1]
        try:
            res = es.index(index=index_name, doc_type='iThome', body=result_json, id=id)
            print (res["result"])
        except:
            print ("Save fail")

if __name__ == "__main__":
    #es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
    logsFunction = LogsFunc("ithome")
    ##爬蟲狀況寫入MySQL
    #sqlc = mysql_conn.ConnectMYsql(mysql_username, mysql_password, mysql_host, mysql_port, mysql_database)
    crawlername = 'ithome'
    isimmediate = True
    Status = 'RUNNING'
    Pid = os.getpid()
    lastupdatetime = datetime.now()
    query = {"query":{"match_all":{}}}
    index_name = "sec_info_ithome"
    index_name_all = index_name + "*"
    total_res = es.search(index=index_name_all, body=query, size=0)
    total = total_res["hits"]["total"]
    #sqlc.update(crawlername, isimmediate, Status, Pid, lastupdatetime, total)
    try:
        if(len(sys.argv) == 1):
            # 啟動時間倒數一年
            delta = timedelta(days=365)
            ithome = IthomeCrawler(datetime.now(), datetime.now()-delta, )
            ithome.parse()
        elif (len(sys.argv) == 2):
            # 啟動時間至輸入時間
            ithome = IthomeCrawler(datetime.now(), datetime.strptime(sys.argv[1],"%Y%m%d"))
            ithome.parse()
        elif (len(sys.argv) == 3):
            # 爬取輸入的時間範圍
            start_time =  datetime.strptime(sys.argv[1],"%Y%m%d")
            end_time =  datetime.strptime(sys.argv[2],"%Y%m%d")
            ithome = IthomeCrawler(start_time, end_time)
            ithome.parse()
        else:
            print ('error')
        print (u"爬蟲完成")
    except Exception as e:
        print (str(e))
        logsFunction.appendWrite(str(e))
    logsFunction.appendWrite('udn')
    print ("Crawler Finish!!!!")
    isimmediate = False
    Status = 'SUCCESS'
    Pid = None
    query = {"query":{"match_all":{}}}
    total_res = es.search(index=index_name_all, body=query, size=0)
    total = total_res["hits"]["total"]
    #sqlc.update(crawlername, isimmediate, Status, Pid, lastupdatetime, total)
    #sqlc.conn.close()
