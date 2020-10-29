#coding=utf-8
import time
import datetime
import json
import sys
import os
import configparser
import requests as rq
#import mysql_schema as mysql_conn
from logsContainer import LogsFunc
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch
from fake_useragent import UserAgent

cf = configparser.ConfigParser()
cf.read(os.path.abspath(os.path.dirname(os.path.abspath(__file__))) +  "/../crawler_config.ini")
es_host = cf.get("Elasticsearch", "HOST")
es_port = cf.get("Elasticsearch", "PORT")
Es_conn = es_host + ":"+ es_port
es = Elasticsearch(Es_conn, timeout=600)
#mysql_username=cf.get("MYSQL", "mysql_username")
#mysql_password=cf.get("MYSQL", "mysql_password")
#mysql_host=cf.get("MYSQL", "mysql_host")
#mysql_port=cf.get("MYSQL", "mysql_port")
#mysql_database=cf.get("MYSQL", "mysql_database")
#sqlc = mysql_conn.ConnectMYsql(mysql_username, mysql_password, mysql_host, mysql_port, mysql_database)
ua = UserAgent()
headers = {'User-Agent': ua.random}
logsFunction = LogsFunc("appledaily")

class AppleDailySpider():
    
    def __init__(self, start = datetime.datetime.today().strftime("%Y%m%d"), end = (datetime.datetime.today() - datetime.timedelta(days=365)).strftime("%Y%m%d")):
        self.start = start
        self.end = end
        self.start_url = "https://tw.appledaily.com/appledaily/archive/" + str(self.start)
        self.lastupdatetime = datetime.datetime.now()

    # 啟動爬蟲
    def spider_start(self):
        # 爬蟲狀況寫入MySQL
        crawlername = 'AppleDaily'
        isimmediate = True
        Status = 'RUNNING'
        Pid = os.getpid()
        query = {"query":{"match_all":{}}}
        total_res = es.search(index="sec_info_appledaily*", body=query, size=0)
        total = total_res["hits"]["total"]
        print("start_total : " + str(total))
        #sqlc.update(crawlername, isimmediate, Status, Pid, self.lastupdatetime, total)
        # log
        logsFunction.appendWrite('appledaily_crawler')
        self.parse()
        self.spider_end()

    # 解析(取得文章列表)
    def parse(self):
        while self.start >= self.end:
            self.start_url = "https://tw.appledaily.com/appledaily/archive/" + str(self.start)
            html = rq.get(self.start_url, headers=headers)
            soup = BeautifulSoup(html.text,'lxml')
            all_news = soup.find('div' ,'abdominis clearmen').find_all('li')   
            for index, news in enumerate(all_news):
                print(self.start + " " + str(index + 1) + " record")
                news_dict = dict()
                if(news.find('a').get('href')[0] == '/'):
                    try:
                        news_dict["URL"] = "https://tw.appledaily.com" + news.find('a').get('href')
                    except:
                        news_dict["URL"] = None
                else:
                    try:
                        news_dict["URL"] = news.find('a').get('href')
                    except:
                        news_dict["URL"] = None
                print(news_dict["URL"])
                url_str_segmentation = news_dict["URL"].split("/")
                if url_str_segmentation[2][0:4] == "home":
                    news_id = str(url_str_segmentation[-4]) + str(url_str_segmentation[-3])
                    self.parse_article_home(news_dict)
                else:    
                    news_id = str(url_str_segmentation[-3]) + str(url_str_segmentation[-2])
                    self.parse_article(news_dict)
                self.sava_data(news_dict, news_id)   
            self.start = (datetime.datetime.strptime(self.start, "%Y%m%d") - datetime.timedelta(days=1)).strftime("%Y%m%d")       

    # 解析文章             
    def parse_article(self, news_dict):
        html = rq.get(news_dict["URL"], headers=headers)
        soup = BeautifulSoup(html.text,'lxml')
        try:
            news_dict["Title"] = soup.find('h1').text
        except:
            news_dict["Title"] = None
        try:
            news_dict["Viewing_Count"] = soup.find('div', 'ndArticle_view').text
        except:
            news_dict["Viewing_Count"] = None
        
        news_dict["Tag"] = None
        news_dict["Reference"] = None
        try:
            news_dict["PublishTime"] = soup.find('div', 'ndArticle_creat').text[5:]
        except:
            news_dict["PublishTime"] = None
        try:
            texts = soup.find('div', 'ndArticle_margin').find_all(['h2', 'p', 'a'])
            news_dict["Description"] = ""
            for text in texts:
                if(text.text[0:4] == u"有話要說"):
                    break
                news_dict["Description"] += (text.text + "\n")
        except:
            news_dict["Description"] = None
        try:
            news_dict["Class"] = soup.find_all('a', 'current')[1].text
        except:
            try:
                if(news_dict["Description"][1:3] == u"工商"):
                    news_dict["Class"] = u"工商消息"
                else:
                    news_dict["Class"] = None
                    print("get type error")
            except:
                news_dict["Class"] = None

    # 解析文章-地產類
    def parse_article_home(self, news_dict):
        html = rq.get(news_dict["URL"], headers=headers)
        soup = BeautifulSoup(html.text,'lxml')
        try:
            news_dict["Title"] = soup.find_all('h1')[1].text
        except:
            news_dict["Title"] = None
        soup.find('time')['datetime']
        
        try:
            news_dict["PublishTime"] = soup.find('time')['datetime'][0:-1]
        except:
            news_dict["PublishTime"] = None
        try:
            texts = soup.find('div', 'articulum').find_all(['h2', 'p'])
            news_dict["Description"] = ""
            for text in texts:
                    news_dict["Description"] += (text.text + "\n")
        except:
            news_dict["Description"] = None
        news_dict["Class"] = u"地產"

    # 儲存資料
    def sava_data(self, news_dict, news_id):
        try:
            create_time_segmentation = news_dict["PublishTime"].split("/")
            es_index = "sec_info_appledaily-" + create_time_segmentation[0] 
            res = es.index(index= es_index, doc_type='appleDaily', id = news_id, body=news_dict)
            print(res['result'])
        except:
            print(u"儲存失敗")

    # 結束爬蟲
    def spider_end(self):
        crawlername = 'appledaily'
        isimmediate = False
        Status = 'SUCCESS'
        Pid = None
        query = {"query":{"match_all":{}}}
        total_res = es.search(index="sec_info_appledaily*", body=query, size=0)
        total = total_res["hits"]["total"]
        print("end_total : " + str(total))
        #sqlc.update(crawlername, isimmediate, Status, Pid, self.lastupdatetime, total)
        #sqlc.conn.close()

if __name__ == '__main__':
    if(len(sys.argv) == 1):
        try:
            appleDailySpider = AppleDailySpider()
            appleDailySpider.spider_start()
            print(u"爬取完成")
        except Exception as e:
            print (str(e))
            logsFunction.appendWrite(str(e))
    elif(len(sys.argv) == 3):
        try:
            appleDailySpider = AppleDailySpider(sys.argv[1], sys.argv[2])
            appleDailySpider.spider_start()
            print(u"爬取完成")
        except Exception as e:
            print (str(e))
            logsFunction.appendWrite(str(e))
    else:
        print('error')
