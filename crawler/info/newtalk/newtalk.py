#-*- coding: utf-8 -*-　
# !/usr/bin/python
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta 
import datetime as dt
import json
from elasticsearch import Elasticsearch
import os
from logsContainer import LogsFunc
#import mysql_schema as mysql_conn
import configparser
from fake_useragent import UserAgent
import sys
import time

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

class NewtalkCrawler():
    
 
    # 解析
    def parse(self):   
        URL_list = "https://newtalk.tw/news/summary/today"  
        response = requests.get(URL_list) 
        soup = BeautifulSoup(response.text, 'lxml')
        try:
            res = es.indices.create(index = index_name)
            print (res)
        except Exception as e :
            #print str(e)
            print ("Index already exists")

        #最上方文章先寫入一次,之後忽略
        top_num = soup.find("div", {"class" : "news-list-item clearfix"}).find("div",{"class" : "news_img col-md-4 col-sm-4 col-xs-6"}).find("a").get("href").split('/')  
#         self.parse_paper(top_num)
        max_page =  dt.date.today() #找今天日期
        
        while True:
            URL = "https://newtalk.tw/news/summary/" + (str)(max_page)
            max_page =max_page + dt.timedelta(days=-1)            
            response = requests.get(URL)  
            soup = BeautifulSoup(response.text, 'lxml')                
            items = soup.find_all("div", {"class" : "news-list-item clearfix"})            
            for item in items:                                
                if "lightbox-handler" not in item.attrs['class']:
                    try:
                        num = item.find("div",{"class" : "news_img col-md-4 col-sm-4 col-xs-6"}).find("a").get("href").split('/')
                        self.parse_paper(num)
                    except:
                        continue 
                        
            if (str)(max_page) =='2009-02-02':
                break

    def parse_paper(self, num):        
        URL_main = "https://newtalk.tw/news/view/" + num[5] + "/" + num[6]
#         print(URL_main)
        response = requests.get(URL_main)
        response.encoding = 'UTF-8'
#         print("encoding: %s" % response.encoding)
        soup = BeautifulSoup(response.text, 'lxml')
        description =""
        tag=""
        
        if soup.find("script") != None and "alert('該篇文章不存在！');" not in soup.find("script").text:
            result_json = dict()                
            postTime = soup.find("div", {"class" : "content_date"}).text.split()[-3]         
            #時間處理(去掉多餘字元)
            fomart = '0123456789/'  
            try: 
                for c in postTime:   
                    if not c in fomart:             
                        postTime = postTime.replace('.','-')    
                result_json["PublishTime"] = postTime.replace('-', '/', 3)
                
            except:
                result_json["PublishTime"] = ''
            
            try:
                result_json["Title"] = soup.find("h1").text
                
            except:
                result_json["Title"] = ''             
            
            try:
                result_json["Class"] = soup.find("div", {"class" : "tag_for_item"}).find_all("a")[-1].text
            except:
                result_json["Class"] = ''   

            try:
                result_json["URL"] = URL_main
            
            except:
                result_json["URL"] = ''
    
            try:
                e = soup.find("div", {"itemprop" : "articleBody"})
                for i in e.find_all("p")[0:-3]:
                    if not i.find("a"):
                        description = description +  i.text
                result_json["Description"] = description
            
            except:
                result_json["Description"] = ''                
            # index_name = "info_newtalk"            
            
            try:           
                date = datetime.strptime(postTime ,'%Y-%m-%d')
            except:
                date = time.strftime('%Y-%m-%d', time.localtime())
                
            try:
                result_json["Viewing_Count"] = ''
            except:
                result_json["Viewing_Count"] = ''
                
            try:
                result_json["Reference"] = ''
            except:
                result_json["Reference"] = '' 
                
            try:
                b = soup.find("div", {"class" : "tag_group2"})
                for t in b.find_all("div", {"class" : "tag_for_item"}):
                    if t.find('a'):
                        tag = tag + t.find('a').text+' '
                        
                result_json["Tag"] = tag

            except:
                result_json["Tag"] = ''   
            
            id = date.strftime('%m') + '_' + date.strftime('%d') + '_' + str(num[6])    
            print (result_json)
            create_time_segmentation = result_json["PublishTime"].split("/")
            es_index = "sec_info_newtalk-" + create_time_segmentation[0] 
            result_json = json.dumps(result_json, ensure_ascii=False)
            try:
                res = es.index(index=es_index, doc_type='newtalk', body=result_json, id=id)
                print (res["result"])
            except:
                print ("Save fail")
            


if __name__ == "__main__":
#    es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
    logsFunction = LogsFunc("newtalk")
   
    #sqlc = mysql_conn.ConnectMYsql(mysql_username, mysql_password, mysql_host, mysql_port, mysql_database)
    crawlername = 'newtalk'
    isimmediate = True
    Status = 'RUNNING'
    Pid = os.getpid()
    lastupdatetime = datetime.now()
    
    index_name = "sec_info_newtalk"    
    

    try:
        newtalk = NewtalkCrawler()
        newtalk.parse()
        print (u"爬蟲完成")
    except Exception as e:
        print (str(e))
        logsFunction.appendWrite(str(e))
    logsFunction.appendWrite('newtalk_crawler')
    isimmediate = False
    Status = 'SUCCESS'
    Pid = None
    query = {"query":{"match_all":{}}}
    total_res = es.count(index=index_name, body=query)
    total =  total_res["count"]
    #sqlc.update(crawlername, isimmediate, Status, Pid, lastupdatetime, total)
    #sqlc.conn.close()
    print ("Crawler Finish!!!!")
