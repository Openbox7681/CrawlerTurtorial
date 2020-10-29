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
import ConfigParser
from fake_useragent import UserAgent
import sys



#Es connect setting
cf = ConfigParser.ConfigParser()
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


class Itncrawler():

    def __init__(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time

    
    # 分類文字轉換
    def class_EngToChi(self, class_name):
        class_list = {
            '/focus/' : '焦點',
            '/politics/' : '政治',
            '/society/' : '社會',
            '/local/' : '地方',
            '/life/' : '生活',
            '/opinion/' : '評論',
            '/world/' : '國際',
            '/business/' : '財經',
            '/sports/' : '體育',
            '/entertainment/' : '影視',
            '/consumer/' : '消費',
            '/people/' : '人物',
            '/ltnrepublic/' : '自由共和國',
            '/culture/' : '文化週報'
        }
        
        return str(class_list[class_name])
    
    # 時間格式轉換
    def date(self, date, soup_paper):
        if not date :
            if soup_paper.find("span", {"class":"viewtime"}):
                date = soup_paper.find("span", {"class":"viewtime"}).text
            else:
                date = soup_paper.find("div", {"class":"writer_date"}).text
        else:
            date = date.strftime('%Y-%m-%d')
        return date
    
    # 內文撈取
    def text(self, soup_paper):
        if soup_paper.find("div", {"itemprop" : "articleBody"}):
            txt_all = soup_paper.find("div", {"itemprop" : "articleBody"})
        else:
            txt_all = soup_paper.find("div", {"class" : "text"})
            
        tags = ["p","h4"]
        text = ''
        for txt in txt_all.find_all(tags):
            text += txt.text + '\n'
        return text
    
    # 取得單篇新聞內容，並存入資料庫
    def get_paper(self,URL, news_txt, date, class_name):
        result_json = dict()
        # 取得單篇新聞URL---------------------------------------------------------------------------
        news_herf = URL + '/' + news_txt.find_all("a")[1].get("href")
        response_paper = requests.get(news_herf)
        soup_paper = BeautifulSoup(response_paper.text, 'lxml')
        
        print news_herf
        # ----------------------------------------------------------------------------------------

        # 將撈得資訊以json格式寫入===================================================================================
        try:
            result_json["Title"] = soup_paper.find("div", {"class" : "content"}).find("h1").text.strip('\n')
        except:
            result_json["Title"] = ''
        try:
            result_json["Class"] = self.class_EngToChi(class_name)
        except:
            result_json["Class"] = ''
        try:
            result_json["URL"] = news_herf
        except:
            result_json["URL"] = ''
        try:
            result_json["Publish_Time"] = self.date(date, soup_paper).strip(' ').split(' ')[0]
            print result_json["Publish_Time"]
        except:
            result_json["Publish_Time"] = ''
        date = datetime.strptime(self.date(date,soup_paper).strip(' ').split(' ')[0] ,'%Y-%m-%d')
#         date = datetime.strptime(date.strip(' ') ,'%Y-%m-%d')

        result_json["Context"] = self.text(soup_paper)
        # ----------------------------------------------------------------------------------------
        # ========================================================================================================

        # 傳入資料庫
        try:
            index = "info_itn_"+ date.strftime('%Y') + '.' + date.strftime('%m')
            id=date.strftime('%m-%d')+"_"+news_herf.split('/')[-1]
            res = es.index(index=index, doc_type=class_name, body=json.dumps(result_json, encoding="UTF-8", ensure_ascii=False), id=id)
            print res["result"]
        except:
            print 'save fail'
        


    # 取得每日更新之新聞
    def get_main_class(self,URL, URL_newspaper, class_name, start_time, end_time):
        date = start_time
        while date >= end_time:
            
            # 得各分類中每天的URL頁面
            URL_class_date = URL_newspaper + class_name + date.strftime('%Y%m%d')
            response = requests.get(URL_class_date)
            soup = BeautifulSoup(response.text, 'lxml')

            
            print class_name
            # 確認該分類頁數
            if soup.find("div", {"class" : "paperEnd"}):
                print "共1頁"
                soup_body = soup.find("div", {"class" : "whitecon boxTitle"}).find("ul", {"class" : "list"}).find_all("li")
                for news_txt in soup_body:
                    self.get_paper(URL, news_txt, date, class_name)
            else:
                all_page = soup.find("div",{"class" : "pagination boxTitle"}).find("a",{"class" : "p_last"}).get("href").split('/')[-1]
                print "共" + all_page + "頁"
                for page in range (1, int(all_page)+1):
                    response = requests.get(URL_class_date + '/' + str(page))
                    soup = BeautifulSoup(response.text, 'lxml')
                    soup_body = soup.find("div", {"class" : "whitecon boxTitle"}).find("ul", {"class" : "list"}).find_all("li")
                    for news_txt in soup_body:
                        self.get_paper(URL, news_txt, date, class_name)
            date -= timedelta(days=1)
                
    # 爬取非每日更新之新聞，人物、自由共和國、文化週報
    def other_class(self, URL, URL_newspaper, class_name):
        response = requests.get(URL_newspaper + class_name)
        soup = BeautifulSoup(response.text, 'lxml')
        all_page = soup.find("div",{"class" : "pagination boxTitle"}).find("a",{"class" : "p_last"}).get("href").split('/')[-1] 
        print "總頁數" + all_page + ", 到" + end_time.strftime('%Y%m%d') + "結束"
        for page in range (1, int(all_page)+1):
            page_href = URL_newspaper + class_name + str(page)
            response = requests.get(page_href)
            soup = BeautifulSoup(response.text, 'lxml')
            soup_body = soup.find("div", {"class" : "whitecon boxTitle"}).find("ul", {"class" : "list"}).find_all("li")
            for news_txt in soup_body:
                news_herf = URL + '/' + news_txt.find_all("a")[1].get("href")
                response_paper = requests.get(news_herf)
                soup_paper = BeautifulSoup(response_paper.text, 'lxml')
                if soup_paper.find("div", {"class":"writer_date"}):
                    if int(soup_paper.find("div", {"class":"writer_date"}).text.split(' ')[0].replace('-',''))<=int(self.end_time.strftime('%Y%m%d')):
                        break
                elif soup_paper.find("span", {"class":"viewtime"}):
                    if int(soup_paper.find("span", {"class":"viewtime"}).text.split(' ')[0].replace('-',''))<=int(self.end_time.strftime('%Y%m%d')):
                        break
                date = None
                self.get_paper(URL, news_txt, date, class_name)
            
            
    # URL解析
    def parse(self):
        
        #組合網址
        URL = "http://news.ltn.com.tw"
        URL_newspaper = URL + "/list/newspaper"
        response = requests.get(URL_newspaper)
        soup = BeautifulSoup(response.text, 'lxml')

        #取得報紙總覽分類清單
        soup_body = soup.find("ul","newsSort boxTitle").find_all("li")
        class_list = []
        for news_class in soup_body:
            class_list.append("/" + news_class.find("a").get("href").split('/')[2] + '/')
        print class_list
        # 依照相同新聞分類開始撈每天的資料
        for list_num in range (0,len(class_list)-3):
            self.get_main_class(URL, URL_newspaper,  class_list[list_num], self.start_time, self.end_time)
        for list_num in range (len(class_list)-3,len(class_list)):
            self.other_class(URL, URL_newspaper, class_list[list_num])

if __name__ == "__main__":
    #es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
    logsFunction = LogsFunc("itn")
    ##爬蟲狀況寫入MySQL
    #sqlc = mysql_conn.ConnectMYsql(mysql_username, mysql_password, mysql_host, mysql_port, mysql_database)
    crawlername = 'itn'
    isimmediate = True
    Status = 'RUNNING'
    Pid = os.getpid()
    lastupdatetime = datetime.now()
    query = {"query":{"match_all":{}}}
    index_name = "info_itn"
    index_name_all = index_name + "*"
    total_res = es.search(index=index_name_all, body=query, size=0)
    total = total_res["hits"]["total"]
    #sqlc.update(crawlername, isimmediate, Status, Pid, lastupdatetime, total)
    try:
        if(len(sys.argv) == 1):
            # 啟動時間倒數一年
            delta = timedelta(days=365)
            itn = Itncrawler(datetime.now(), datetime.now()-delta, )
            itn.parse()
        elif (len(sys.argv) == 2):
            # 啟動時間至輸入時間
            itn = Itncrawler(datetime.now(), datetime.strptime(sys.argv[1],"%Y%m%d"))
            itn.parse()
        elif (len(sys.argv) == 3):
            # 爬取輸入的時間範圍
            start_time =  datetime.strptime(sys.argv[1],"%Y%m%d")
            end_time =  datetime.strptime(sys.argv[2],"%Y%m%d")
            itn = Itncrawler(start_time, end_time)
            itn.parse()
        else:
            print 'error'
        print u"爬蟲完成"
    except Exception as e:
        print str(e)
        logsFunction.appendWrite(str(e))
    logsFunction.appendWrite('udn')
    print "Crawler Finish!!!!"
    isimmediate = False
    Status = 'SUCCESS'
    Pid = None
    query = {"query":{"match_all":{}}}
    total_res = es.search(index=index_name_all, body=query, size=0)
    total = total_res["hits"]["total"]
    #sqlc.update(crawlername, isimmediate, Status, Pid, lastupdatetime, total)
    #sqlc.conn.close()

        
