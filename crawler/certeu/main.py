#!/usr/bin/python3
# -*- coding: utf-8 -*-

import re
import requests
import calendar
import sys
import datetime
import time

import click
import schedule
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch

from logContainer import LogsFunc

'''新增每一筆新聞資料'''
def insert(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.text.encode("utf-8"), 'lxml')
    
    articles2 = soup.find_all("div", class_="articlebox_big")
    for i in range(0, len(articles2)):
        try:
            '''新聞標題'''
            title = (articles2[i].find_all("a", class_="headline_link"))[0].text
            # print(title)
            url = (articles2[i].find_all("a", class_="headline_link", href=True))[0]
            url = url['href']            

            detail = (articles2[i].find_all("p", class_="center_headline_source"))
            time = detail[0].text
            # print(time)
            
            '''時間'''
            string = '.*?,\s([a-zA-Z]*)\s(\d{1,2}),\s(\d{4})\s(\d{1,2}):(\d{2}):(\d{2})\s(AM|PM)\sCE'
            time2 = (re.findall(string, time)[0])
            # print('get: ', time2)
            months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
            months_Eng = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
                            "October",
                            "November", "December"]
            month = str(time2[0])
            # print(month)
            for m in range(0, len(months_Eng)):
                if month == months_Eng[m]:
                    month = months[m]

            if time2[6] == 'PM':#判斷今天或明天
                try:
                    time3 = datetime.datetime(int(time2[2]), int(month), int(time2[1]), int(time2[3]) + 12,
                                                int(time2[4]), int(time2[5]))
                except:
                    # print('change to next day 0 AM: ')
                    try:
                        time3 = (
                            datetime.datetime(int(time2[2]), int(month), int(time2[1]) + 1, int(0), int(time2[4]),
                                                int(time2[5])))
                        # print(time3)
                    except:
                        # print('change to next month 1 th: ')
                        try:
                            time3 = (
                                datetime.datetime(int(time2[2]), (int(month) + 1), int(1), int(0), int(time2[4]),
                                                    int(time2[5])))
                            # print(time3)
                        except:
                            # print('change to next year + 1 : ')
                            time3 = (datetime.datetime(int(time2[2]) + 1, int(1), int(1), int(0), int(time2[4]),
                                                        int(time2[5])))
                            # print(time3)
            else:
                time3 = datetime.datetime(int(time2[2]), int(month), int(time2[1]), int(time2[3]), int(time2[4]),
                                            int(time2[5]))

            # print(time3)

            '''依據新聞時間取出年份，新增到該年的es'''
            year=time3.year
            esname="sec_certeu-"+str(year)
            #建立es 的index，依據年份
            try:
                res = ES_ip.indices.create(index = esname)
                # print(res)
            except Exception as e :
                # print("Index already exists")
                pass
            
            time3 = int(time3.strftime("%s")) * 1000
            # print(time3)

            '''國家'''
            country = str(articles2[i].find_all("img", class_="source_flag_icon")[0])
            string = 'src=".*?\/(.[A-Z{2}]).gif'
            country2 = str(re.findall(string, country)[0])
            # print('get: country', country2)

            '''新聞網站名稱'''
            web = None
            try:
                web = articles2[i].findAll("p", class_="center_headline_source")[0].text
                string = ' (.*?)\s.*?,\s[a-zA-Z]*\s\d{1,2},\s\d{4}\s\d{1,2}:\d{2}:\d{2}\sAM|PM\sCET'
                web = (re.findall(string, web)[0])
                # print('web: ',web)
            except:
                web = None

            '''新聞內文'''
            description = (articles2[i].find_all("p", class_="center_leadin"))[0].text
            # print(description)

            '''關鍵字'''
            trigger_words = (articles2[i].find_all("p", class_="center_reason"))[0].text
            # print('trigger_words: ',trigger_words)
            trigger_words = trigger_words.replace('Trigger words: [CERT-LatestNews] (Threats)', '')
            trigger_words = trigger_words[(0):(len(trigger_words) - 2)]
            # print('trigger_words: ',trigger_words)
            trigger_words = trigger_words.split('; ')
            for k in range(0, len(trigger_words)):
                # print('words: ', trigger_words[k])
                trigger_words[k] = (trigger_words[k])[(0):(len(trigger_words[k]) - 3)]
                # replace [1] [2] [11]...
                # print(trigger_words[k])
            # print('trigger_words: ', trigger_words)

            '''類別'''
            categories = str((articles2[i].find_all("p", class_="center_also"))[0].text)
            # print('categories: ',categories)
            categories = categories.replace('Other categories: ', '')
            categories = categories[(0):(len(categories) - 2)]
            # print('categories: ',categories)
            categories = categories.split('; ')
            # print('categories: ', categories)

            featureJson = {
                "title": title,
                "url": url,
                "publish_date": time3,
                "country": country2,
                "web": web,
                "content": description,
                "trigger_words": trigger_words,
                "category": categories
            }
            #print(featureJson)

            query = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "query_string": {
                                    "default_field": "articles.url.keyword",
                                    "query": "url:\""+str(url)+"\""
                                }
                            }
                        ]
                    }
                }
            }
            response = ES_ip.search(index=esname, doc_type="articles", body=query)
        
            if len(response["hits"]["hits"]) > 0:
                '''已在資料庫裡，無需新增'''
                pass
                # ES_ip.index(index=esname, doc_type='articles', body=featureJson, id=response["hits"]["hits"][0]["_id"])

            else:
                '''需要新增'''
                print('---------add: '+url)
                ES_ip.index(index=esname, doc_type='articles', body=featureJson)
                logsFunction.appendWrite('新增: '+str(url))

        except Exception as e:
            print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

def get_certeu():    
    logsFunction.appendWrite('開始抓certeu的資料')
    '''每次抓取前3頁資料'''
    for i in range(0, 3):
        url = "https://cert.europa.eu/cert/dynamic?language=en&page=" + str(i) + "&edition=categoryarticles&option=CERT-LatestNews&_=1509521884302"
        print("page: ", str(i))
        insert(url)
    logsFunction.appendWrite('結束抓certeu的資料')
@click.command()
@click.option('--es_ip', type=str,default='192.168.163.51')
@click.option('--es_port', type=str, default='59200')
#30分鐘執行一次
def run(es_ip,es_port):
    global ES_ip
    ES_ip = Elasticsearch(es_ip + ":" + es_port)
    '''log紀錄執行狀況'''
    global logsFunction
    logsFunction = LogsFunc("certeu")

    get_certeu()
    
if __name__ == '__main__':
    run()