#-*- coding: utf-8 -*-　
# !/usr/bin/python
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import datetime
import time
import sys
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from elasticsearch import Elasticsearch

import HTMLParser
import logging
import os
import mysql_schema as mysql_conn
import ConfigParser
from fake_useragent import UserAgent

def get_title(class_lists ,time_end ,time_start):
    	
        for s in class_lists:
            response = requests.get(s)
            soup = BeautifulSoup(response.text, 'lxml')
            soup_body=soup.find("div", {"class":"left"}).find_all("div",{"class":"item_inner"})
            driver= webdriver.Chrome()#模擬網頁
            driver.get(s)
            time.sleep(2)#等待二秒
            try :
                noad=driver.find_element_by_class_name('bx_icon')#關閉廣告
                noad.click()#關閉廣告
            except:
                time.sleep(0.1)
            a=0
            lateTime=[]
            for body in soup_body:
                lateTime.append(body.find("div",{"class":"div_td td1"}).text)
            while a<1:
                try :
                    lowtime = datetime.datetime.strptime(lateTime[-1], "%Y-%m-%d")
                    print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
                    print lowtime
                    print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
                    if time_start<=lowtime:
                        button = driver.find_element_by_class_name('more_btn')#更多內容
                        button.click()#更多內容
                        time.sleep(3)#等待3秒
                        html_source = driver.page_source#重新刷新HTML內容
                        time.sleep(3)#等待3秒
                        soup = BeautifulSoup(html_source, 'lxml')#重新抓取HTML內容
                        soup_body=soup.find("div", {"class":"left"}).find_all("div",{"class":"item_inner"})
                        for body in soup_body:
                            lateTime.append(body.find("div",{"class":"div_td td1"}).text)
                    else:
                        a=a+2
                except:
                    button = driver.find_element_by_class_name('more_btn')#更多內容
                    button.click()#更多內容
                    time.sleep(3)#等待3秒
                    html_source = driver.page_source#重新刷新HTML內容
                    time.sleep(3)#等待3秒
                    soup = BeautifulSoup(html_source, 'lxml')#重新抓取HTML內容
                    soup_body=soup.find("div", {"class":"left"}).find_all("div",{"class":"item_inner"})
            
           
            
            class_lists_paper=[]
            for body in soup_body:
                class_lists_paper.append(body.find("a",{"class":"item_img bg_img_sty01"}).get("href"))
                lateTime.append(body.find("div",{"class":"div_td td1"}).text)
            
            class_name=soup.find("div",{"class":"title"}).text
            # get_content(class_lists_paper ,class_name ,time_start ,time_end)

def get_content( class_lists_paper ,class_name,time_start ,time_end):
       	result_json = dict()
        for d in class_lists_paper:
            response = requests.get(d)
            soup = BeautifulSoup(response.text, 'lxml')
            Article_title=soup.find("title")
            Article_time=soup.find("span",{"class":"item"}).text
            Article_timenew = datetime.datetime.strptime(Article_time, "%Y.%m.%d")
            Article_acontent=soup.find("article",{"class":"main_content"}).find_all("p")
            try :
                Article_tag=soup.find("div",{"class":"article_tags"}).find_all("a")
            except:
                Article_tag=""
            index="info_chinatimes_"
            types="chinatimes"
            tags=""
            acontentall=""
            url=d.split("/", 5)
            
            for content in Article_acontent:
                acontentall=acontentall+"\n"+content.text
            for tag in Article_tag:
                tags=tags+tag.text
            print "+++++++++++++++++++++"
            print time_start
            print time_end
            print "---------------------"
            if time_end>=Article_timenew:
                if time_start<= Article_timenew:
                    result_json["Title"] = Article_title.text
                    result_json["Class"] = class_name
                    result_json["URL"] = d
                    result_json["Publish_Time"] = Article_time
                    result_json["Description"] = acontentall
                    print result_json["Title"]
                    print result_json["Publish_Time"]
                    sqlc.update(crawlername, isimmediate, Status, Pid, lastupdatetime, total)


                    # print result_json["Publish_Time"]
                    # print result_json["Title"]
                    # # 傳入資料庫
                    # try:
                    #     index = index+Article_time[:7]
                    #     id=Article_time+"_"+url[4]
                    #     res = es.index(index=index, doc_type="chinatimes", body=json.dumps(result_json, encoding="UTF-8", ensure_ascii=False), id=id)
                    #     print res["result"]
                    # except:
                    #     print 'save fail'
                else:
                    break
           
if __name__ == '__main__':
    cf = ConfigParser.ConfigParser()
    #Es connect setting
    cf.read(os.path.abspath(os.path.dirname(os.path.abspath(__file__))) +  "/../../lib/crawler_config.ini")
    es_host = cf.get("Elasticsearch", "HOST")
    es_port = cf.get("Elasticsearch", "PORT")
    mysql_username = cf.get("MYSQL", "mysql_username")
    mysql_password = cf.get("MYSQL", "mysql_password")
    mysql_host = cf.get("MYSQL", "mysql_host")
    mysql_port = cf.get("MYSQL", "mysql_port")
    mysql_database = cf.get("MYSQL", "mysql_database")
    Es_conn = es_host + ":"+ es_port
    es = Elasticsearch(Es_conn, timeout=600)

    #Es connect setting

    # SQL連線
    if len(sys.argv) == 1:
        time_end = datetime.datetime.now()-datetime.timedelta(days=1)
        time_start = time_end - datetime.timedelta(days=7)
    else:
        time_start=sys.argv[1]
        time_start = datetime.datetime.strptime(time_start, "%Y%m%d")
        time_end = sys.argv[2]
        time_end = datetime.datetime.strptime(time_end, "%Y%m%d")
    sqlc = mysql_conn.ConnectMYsql(mysql_username,mysql_password,mysql_host,mysql_port,mysql_database)
    # 參數設定
	##爬蟲狀況寫入MySQL

    crawlername='chinatimes'
    isimmediate = True
    Status = 'RUNNING'
    Pid = os.getpid()
    lastupdatetime = datetime.datetime.now()
    #開始爬蟲j
    URL_main = "https://www.bnext.com.tw/"
    response = requests.get(URL_main)
    soup = BeautifulSoup(response.text, 'lxml')
    soup_body = soup.find("div", {"class":"menu_box row"}).find_all("div", {"class":"title_sty01"})
    index_name = 'info_chinatimes'
    index_name_all = index_name + "*"
    query = {"query":{"match_all":{}}}
    total_res =es.count(index=index_name_all, body=query)
    total =  total_res["count"]
    print total
    sqlc.update(crawlername, isimmediate, Status, Pid, lastupdatetime, total)
    #取得分類
    class_lists = []
    a=0
    for body in soup_body:
        class_lists.append(URL_main + body.find("a").get("href"))
        a=a+1
        if a==10:
            break
    get_title(class_lists,time_end,time_start)#將class_lists陳列資料都到parse_2方式中
    print "Crawler Finish!!!!"
    isimmediate = False
    Status = 'SUCCESS'
    Pid = None
    query = {"query":{"match_all":{}}}
    total_res = es.count(index=index_name_all, body=query)
    total =  total_res["count"]
    sqlc.update(crawlername, isimmediate, Status, Pid, lastupdatetime, total)
    sqlc.conn.close()

    #取得分類
