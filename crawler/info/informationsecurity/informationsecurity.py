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
import time
# reload(sys)                      
# sys.setdefaultencoding('utf-8') 

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

class InformationsecurityCrawler():
    
    def __init__(self, total):
        self.total = total        
    
    # 解析
    def parse(self):   
        URL_list = "https://www.informationsecurity.com.tw/article/article_list.aspx"  
        response = requests.get(URL_list) 
        soup = BeautifulSoup(response.text, 'lxml')  
        #最上方文章先寫入一次,之後忽略
        top_num = (int)(soup.find("div", {"class" : "pic_word_box"}).find("div",{"class" : "center_box_title"}).find("a").get("href").split('=')[-1])
        self.parse_paper(top_num)        
        max_page = (int)(soup.find("span",{"id" : "ctl00_ContentPlaceHolder1_LblCurPage"}).text.split(' ')[-1])       
        max_page = max_page     
         
        for list_num in range (1, max_page, 1):               
            URL = URL_list + "?Page=" + (str)(list_num)
            response = requests.get(URL)  
            soup = BeautifulSoup(response.text, 'lxml')                
            items = soup.find_all("div", {"class" : "pic_word_box"})            
            for item in items:                                
                if "clear" not in item.attrs['class']:
                    num = (int)(item.find("div",{"class" : "center_box_title"}).find("a").get("href").split('=')[-1])
                    self.parse_paper(num)      

    def parse_paper(self, num):
        URL_main = "https://www.informationsecurity.com.tw/article/article_detail.aspx?aid=" + str(num)            
        response = requests.get(URL_main)           
        soup = BeautifulSoup(response.text, 'lxml')                             
        if soup.find("script") != None and "alert('該篇文章不存在！');" not in soup.find("script").text:
            result_json = dict()                
            postTime = soup.find("div", {"class" : "article_editor"}).text.split('-')[-1]                          
            #時間處理(去掉多餘字元)
            fomart = '0123456789/'  
            try: 
                for c in postTime:   
                    if not c in fomart:
                        postTime = postTime.replace(c,'')             
                postTime = postTime.replace('/','-')    
                result_json["PublishTime"] = postTime.replace('-', '/', 3)                   
            except:
                result_json["PublishTime"] = ''
            try:
                result_json["Title"] = soup.find("h1").text
            except:
                result_json["Title"] = ''
            try:
                result_json["Class"] = soup.find("div", {"class" : "article_detail_breadcrumbs"}).find_all("a")[-1].text
            except:
                result_json["Class"] = ''
            try:
                result_json["URL"] = URL_main 
            except:
                result_json["URL"] = ''
            try:
                result_json["Description"] = soup.find("div", {"class" : "article_detail_text"}).text.strip('\n')
            except:
                result_json["Description"] = ''
            result_json["Tag"] = None
            result_json["Reference"] = None
            result_json["Viewing_Count"] = None
                
            try:           
                date = datetime.strptime(postTime.strip(' ') ,'%Y-%m-%d')
            except:
                date = time.strftime("%Y-%m-%d", time.localtime())
            id = date.strftime('%m') + '_' + date.strftime('%d') + '_' + str(num)
            try:
                create_time_segmentation = result_json["PublishTime"].split("/")
                es_index = "sec_info_informationsecurity-" + create_time_segmentation[0] 
                res = es.index(index=es_index, doc_type='informationsecurity', body=result_json, id=id)
                print(res['result'])
            except:
                print(u"儲存失敗")                   



if __name__ == "__main__":
    #es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
    index_name = "sec_info_informationsecurity"

    try:
        res = es.indices.create(index = index_name)
    except Exception as e:
        print ("It's always create")


    logsFunction = LogsFunc("informationsecurity")
    ##爬蟲狀況寫入MySQL
    #sqlc = mysql_conn.ConnectMYsql(mysql_username, mysql_password, mysql_host, mysql_port, mysql_database)
    crawlername = 'informationsecurity'
    isimmediate = True
    Status = 'RUNNING'
    Pid = os.getpid()
    lastupdatetime = datetime.now()
    query = {"query":{"match_all":{}}}
    total_res = es.count(index=index_name, body=query)
    total = total_res['count']
    print (total)
    #sqlc.update(crawlername, isimmediate, Status, Pid, lastupdatetime, total)
    try:
        informationsecurity = InformationsecurityCrawler(total)
        informationsecurity.parse()
        print (u"爬蟲完成")
    except Exception as e:
        print (str(e))
        logsFunction.appendWrite(str(e))
    logsFunction.appendWrite('udn')
    isimmediate = False
    Status = 'SUCCESS'
    Pid = None
    query = {"query":{"match_all":{}}}
    total_res = es.count(index=index_name, body=query)
    total = total_res['count']
    #sqlc.update(crawlername, isimmediate, Status, Pid, lastupdatetime, total)
    #sqlc.conn.close()
    print ("Crawler Finish!!!!")
