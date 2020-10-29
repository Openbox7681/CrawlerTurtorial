#!/usr/bin/python3
# -*- coding: utf-8 -*-
import time
from datetime import datetime
import calendar
import re
import requests
import json
import sys

import click
import schedule
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch

from logContainer import LogsFunc

'''新增每一筆cve id 的資料'''
def insert(match,times,esname):
    for i in range(0, len(match)):
        u = str('https://www.cvedetails.com/cve/') + str(match[i][1])
        print(u)
    
        try:
            res = requests.get(u,stream=True)
            soup = str(BeautifulSoup(res.text.encode("utf-8"), features="lxml"))
            # print soup

            '''cve影響的產品，包含type(產品類別)、vendor(廠商)、product(產品)、version(版本)、update(更新版)、edition(發行版)、language(語言)'''
            string = '<td class="num">\s*\d*\s*<\/td>\s*<td>\s*(.*?)\s*<\/td>\s*<td>\s*<a href=".*?" title=".*?">(.*?)<\/a>\s*<\/td>\s*<td>\s*<a href=".*?" title=".*?">(.*?)<\/a>\s*<\/td>\s*<td>\s*(.*?)\s*<\/td>\s*<td>\s*(.*?)\s*<\/td>\s*<td>\s*(.*?)\s*<\/td>\s*<td>\s*(.*?)\s*<\/td>'
            ProductsAffected = re.findall(string, soup)
            # print("ProductsAffected: ",ProductsAffected)

            productaffected = []
            for type_, vendor_, product_, version_ ,update_, edition_, language_ in ProductsAffected:
                productaffected.append(
                    {"type": type_, "vendor": vendor_, "product": product_, "version": version_, "update": update_, "edition": edition_, "language": language_})

            '''cve的類型'''
            vultype = []
            string = '<tr>\s*<th>Vulnerability Type.*?<\/th>\s*<td>\s*<span class=".*?">(.*?)<\/span>\s*<\/td>\s*<\/tr>'

            try:
                a = (re.findall(string, soup)[0])
                # print(a)
                while True:
                    index_1 = a.find("<")
                    if index_1 > -1:
                        index_2 = a.find("\">")
                        b = a[(index_1):(index_2 + 2)]
                        a = a.replace(b, ',')
                    else:
                        break

                for t in a.split(','):
                    vultype.append(t)

            except:
                vultype = None

            '''cve的資料'''
            featureJson = {
                "CVE_ID": match[i][1],
                "url": u,
                "Products_Affected": productaffected,
                "vultype": vultype,
                "publish_date":times[i][0],
                "update_date":times[i][1]
            }
            print("update_date ",times[i][1])
            print(json.dumps(featureJson, indent=2))

            '''到es撈資料'''
            query = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "query_string": {
                                    "default_field": "cvedetails.CVE_ID",
                                    "query": "CVE_ID:\"" + str(match[i][1]) + "\""
                                }
                            }
                        ]
                    }
                }
            }
            response = ES_ip.search(index=esname, doc_type="cvedetails", body=query)
            #print response
            if len(response["hits"]["hits"]) > 0:#更新
                print("updating: ", str(match[i][1]))
                logsFunction.appendWrite('更新： '+str(match[i][1]))
                ES_ip.index(index=esname, doc_type='cvedetails', body=featureJson,id=response["hits"]["hits"][0]["_id"])
                # time.sleep(1)
            else:#新增
                print("add: ", str(match[i][1]))
                logsFunction.appendWrite('新增： '+str(match[i][1]))
                ES_ip.index(index=esname, doc_type='cvedetails', body=featureJson)
                # time.sleep(1)
        except Exception as e:
            print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

'''進入每一頁，抓cve'''
def getPages(p,esname):
    '''翻開每一頁，抓cve'''
    for page in p:
        page = page.replace('amp;', '')

        res = requests.get("https://www.cvedetails.com" + page)
        print("https://www.cvedetails.com" + page)
        soup = str(BeautifulSoup(res.text.encode("utf-8"),'lxml'))
        
        '''找出cve id和連結'''
        string = '<td nowrap=""><a href="(.*?)"\s*title=".*? security vulnerability details">(.*?)<\/a><\/td>'
        cve_ = re.findall(string, soup)
        # print('There are ', len(cve_), ' vulnerabilities in this page.')

        '''找出時間：建立時間與更新時間，目的是要判斷需不需要更新資料'''
        string = '<td>(\d{4}\-\d{2}\-\d{2})<\/td>\s*<td>(\d{4}\-\d{2}\-\d{2})<\/td>'
        times_ = re.findall(string, soup)
        # print(times_)
    
        '''儲存要回傳的cve資料'''
        cve=[]
        times=[]

        for i in range(0,len(cve_)):

            #建立時間
            publish_date_ = datetime.strptime(times_[i][0], '%Y-%m-%d')
            publish_date_ = calendar.timegm(datetime.timetuple(publish_date_)) * 1000

            #更新時間
            update_date_ = datetime.strptime(times_[i][1], '%Y-%m-%d')
            update_date_ = calendar.timegm(datetime.timetuple(update_date_)) * 1000

            query = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "query_string": {
                                    "default_field": "cvedetails.CVE_ID.keyword",
                                    "query": "CVE_ID:\"" + str(cve_[i][1]) + "\""
                                }
                            }
                        ]
                    }
                }
            }
            response = ES_ip.search(index=esname, body=query)
            # print('last_update_date_',response["hits"]["hits"][0]["_source"]["update_date"])
            
            try:
                '''撈出上次更新的時間，較舊的話即需要更新'''
                last_update_date_ =response["hits"]["hits"][0]["_source"]["update_date"] 
                # print('last_update_date_',last_update_date_)
                #如果有在es而且更新時間比較舊，那就需要更新
                if len(response["hits"]["hits"]) > 0 and last_update_date_<update_date_:
                    print(str(cve_[i][1]),' last_update_date_ < update_date_ ',last_update_date_,update_date_)
                    cve.append(cve_[i])
                    times.append([publish_date_,update_date_])
                    print('有在es而且時間比較舊，需要更新')
                else:#不用更新
                    print('有在es而不用更新')
                #     print('else last_update_date_ >=  update_date_')
                #     print('last_update_date_ , update_date_',last_update_date_,update_date_)
            except:#沒有在es裡面，也需要新增
                print(cve_[i][1],str(' 沒有在es裡面，需要新增'))
                cve.append(cve_[i])
                times.append([publish_date_,update_date_])
        print('需要更新的筆數： ',len(cve))

        '''進入每一個cve，更新資料，參數：[連結,cve-id]、[創建時間,更新時間]'''
        insert(cve,times,esname)

'''進入每一個月，抓每一頁的資料'''
def getmonth(y, m, month):
    '''抓每一個月中的每一頁'''
    url = "https://www.cvedetails.com/vulnerability-list/year-" + str(y) + "/month-" + str(m) + "/" + str(month) + ".html"
    res = requests.get(url)
    # print('year month ',year,month)

    soup = str(BeautifulSoup(res.text.encode("utf-8"),'lxml'))
    # print(soup)

    '''撈出每一月裡面的頁面連結'''
    string = '<a href="(\/vulnerability-list\.php\?.*?)" title=".*?">\d*<\/a>'
    pages = re.findall(string, soup)
    # print(len(pages))
    esname="sec_cvedetails-"+str(y)

    '''建立es 的index，依據年份'''
    try:
        mapping='{"settings": {"index.mapping.ignore_malformed": true}}'
        res = ES_ip.indices.create(index=esname, body=mapping)
        # print(res)
    except Exception as e :
        # print("Index already exists")
        pass
    
    '''抓每一頁裡面的每一個cve'''
    getPages(pages,esname)

def getcvedetails():
    '''log紀錄執行狀況'''
    logsFunction.appendWrite('cvedetails')

    '''抓現在的時間'''
    global t 
    t= datetime.now()
    print('The time is : ', t)
    global y
    y= t.year
    m=t.month
    
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October","November", "December"]

    #現在是1月的時候 爬到去年12月
    if (m == 1):

        logsFunction.appendWrite('開始抓'+str(y)+'/'+ str(m)+'月的資料')
        getmonth(y, m, months[m-1])
        print('crawler cvedetails: ', y, '/', m, months[m-1],' finish!')
        logsFunction.appendWrite('開始抓'+str(y-1)+'/'+ str(12)+'月的資料')
        getmonth(y-1, 12, months[m - 2])
        print('crawler cvedetails: ', y-1, '/',12, months[m-2],' finish!')  

    #抓當月以及上一個月的
    else:
        logsFunction.appendWrite('開始抓'+str(y)+'/'+ str(m)+'月的資料')
        getmonth(y, m-1, months[m - 2])
        print('crawler cvedetails: ', y, '/', m-1, months[m-2],' finish!')
        logsFunction.appendWrite('開始抓'+str(y)+'/'+ str(m-1)+'月的資料')
        getmonth(y, m, months[m-1])
        print('crawler cvedetails: ', y, '/', m, months[m-1],' finish!')

@click.command()
@click.option('--es_ip', type=str,default='192.168.163.51')
@click.option('--es_port', type=str, default='59200')
#60分鐘一次
def run(es_ip,es_port):
    global ES_ip
    ES_ip = Elasticsearch(es_ip + ":" + es_port)
    '''log紀錄執行狀況'''
    global logsFunction
    logsFunction = LogsFunc("cvedetails")
    getcvedetails()

if __name__ == '__main__':
    run()