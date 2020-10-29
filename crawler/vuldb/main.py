#!/usr/bin/python3
# -*- coding: utf-8 -*-
import re
import time
import requests
from datetime import datetime
import sys
import json
from random import randint
import os

import click
import schedule
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch
from selenium import webdriver
from selenium.webdriver.common import action_chains, keys  # keys.Keys
from selenium.webdriver.support.ui import WebDriverWait

from logContainer import LogsFunc

def get_vuldb(chromedrive_path):
    '''抓現在的時間'''
    year = datetime.now().year
    # year=2018
    month=datetime.now().month
    print('crawler vuldb: ', year)

    '''建立es index'''
    esname="sec_vuldb-"+str(year)
    try:
        mapping='{"settings": {"index.mapping.ignore_malformed": true}}'
        res = ES_ip.indices.create(index=esname, body=mapping)
        # print(res)
    except Exception as e :
        # print("Index already exists")
        pass

    '''開啟chrome driver並登入'''
    url = "https://vuldb.com/?login"

    if chromedrive_path is None:
        '''取得當下目錄'''
        current_path = os.path.abspath(__file__)
        '''取得chromedeiver路徑'''
        chromedrive_path=os.path.join(os.path.abspath(os.path.dirname(current_path) + os.path.sep ),'chromedriver')
    else:
        chromedrive_path = os.path.join(chromedrive_path, 'chromedriver')
    print(chromedrive_path)

    '''設置 webdriver參數'''
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-dev-shm-usage')
    '''以headless方案運行'''
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')


    global driver
    driver = webdriver.Chrome(chromedrive_path,options=options)
    # driver = webdriver.Chrome()
    driver.implicitly_wait(30)
    driver.get(url)
    wait = WebDriverWait(driver, 10)

    '''登入'''
    button_usernamebox = driver.find_element_by_xpath("//input[@id='user']").send_keys('benrosb')
    button_passwordbox = driver.find_element_by_xpath("//input[@id='password']").send_keys('buffalo150608')
    button_searchstart = driver.find_element_by_xpath("//input[@value='Login']").click()

    '''進入每年的清單網頁'''
    driver.get("https://vuldb.com/?archive.{}".format(year))
    soup = str(BeautifulSoup(driver.page_source, 'lxml'))

    '''取出該年每個月的連結'''
    string = '<a href="(\?archive\.'+str(year)+'\d*)">'
    match = re.findall(string, soup)

    '''抓取每個月的漏洞清單'''
    for i in match:
        url = "https://vuldb.com/"+str(i)
        driver.get(url)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        #取得列表中原始碼
        title_list  = soup.find("tbody")
        '''進入漏洞細部頁面'''
        if title_list is not None:
            title_list = title_list.find_all("tr")
            print('There are ', len(title_list), ' vulnerabilities in : ', url)
            insert_cve(title_list,esname)
        else:
            print('There are no vulnerabilities in : ', url)
    print('crawler vuldb: ', year,' finish!')


'''新增每一筆cve的資料'''
def insert_cve(title_list,esname):


    for item in title_list:
        time.sleep(randint(5, 10))
        title = item.find_all("td")
        url = 'https://vuldb.com/' + title[3].find("a").get("href")
        query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "query_string": {
                                "default_field": "vuldb.url.keyword",
                                "query": "url:\"" + url + "\""
                            }
                        }
                    ]
                }
            }
        }
        response = ES_ip.search(index=esname,body=query)

        try :
            url = 'https://vuldb.com/' + title[3].find("a").get("href")
            print(url)
            driver.get(url)
            soup = str(BeautifulSoup(driver.page_source, 'lxml'))
            timelinestring = '(\d{2}\/\d{2}\/\d{4})<\/span> <span class="timeline-.*?"><\/span>'
            timeline = re.findall(timelinestring, str(soup))

            risk=None
            risk_score = float(title[1].getText())
            if 0 < risk_score < 4:
                risk = 'low'
            elif 4 <= risk_score <7:
                risk = 'medium'
            elif 7 <= risk_score <=10:
                risk = 'high'
            '''零日價格'''
            zeroday_range =  title[4].getText()
            zeroday_upper = re.findall('\$(\d*)-\$(\d*)', zeroday_range.replace('k', ''))[0][0]
            zeroday_lower = re.findall('\$(\d*)-\$(\d*)' , zeroday_range.replace('k', ''))[0][1]
            '''現今價格'''
            today_range = title[5].getText()
            today_lower =re.findall('\$(\d*)-\$(\d*)', today_range.replace('k', ''))[0][0]
            today_upper =re.findall('\$(\d*)-\$(\d*)', today_range.replace('k', ''))[0][1]
            '''更新資料'''
            if len(response["hits"]["hits"]) > 0:
                print('Already exists, update...',url)

                updatetime = timeline[(len(timeline)-1)]#get the last time to be update time
                # print("updatetime",updatetime)
                updatetime = datetime.strptime(updatetime, '%m/%d/%Y')
                # print("updatetime",updatetime)
                updatetime = int(updatetime.timestamp())
                # print("updatetime",updatetime)

                zeroday_initialtime = timeline[0]#get the first time to be initial time
                zeroday_initialtime = datetime.strptime(zeroday_initialtime, '%m/%d/%Y')
                print("zeroday_initialtime",zeroday_initialtime)
                zeroday_initialtime = int(zeroday_initialtime.timestamp())
                print("zeroday_initialtime",zeroday_initialtime)

                '''若價格有更新則保存歷史價格，加入新價格'''
                today_price_history=(response["hits"]["hits"][0]["_source"]["today_price"])#get price from es
                today_price_history_newest_range=today_price_history[len(today_price_history)-1]["range"] #get the newset price range
                today_price=today_price_history
                if today_price_history_newest_range!=today_range:
                    today_price.append({"range": today_range, "lower": today_lower, "upper": today_upper,"time":updatetime})

                zeroday_price_history=(response["hits"]["hits"][0]["_source"]["zeroday_price"])#get price from es
                zeroday_price_history_newest_range=zeroday_price_history[len(zeroday_price_history)-1]["range"] #get the newset price range
                zeroday_price=zeroday_price_history
                if zeroday_price_history_newest_range!=zeroday_range:
                    zeroday_price.append({"range": zeroday_range, "lower": zeroday_lower, "upper": zeroday_upper,"time":updatetime})

                featureJson = {
                    'CVE_ID': title[8].getText(),
                    'risk': risk,
                    'url': url,
                    'zeroday_price': zeroday_price,
                    'today_price': today_price,
                    'publish_date':zeroday_initialtime
                }
                ES_ip.index(index=esname, doc_type='vuldb', body=featureJson,id=response["hits"]["hits"][0]["_id"])
                logsFunction.appendWrite('update : '+str(url))
            else:
                '''新增資料'''
                print('Add...',url)
                today_updatetime = timeline[(len(timeline)-1)]#get the last time to be update time
                today_updatetime = datetime.strptime(today_updatetime, '%m/%d/%Y')
                print("today_updatetime",today_updatetime)
                today_updatetime = int(today_updatetime.timestamp())
                print("today_updatetime",today_updatetime)

                print("today_updatetime",today_updatetime)
                zeroday_initialtime = timeline[0]#get the first time to be initial time
                zeroday_initialtime = datetime.strptime(zeroday_initialtime, '%m/%d/%Y')
                print("zeroday_initialtime",zeroday_initialtime)
                zeroday_initialtime = int(zeroday_initialtime.timestamp())
                print("zeroday_initialtime",zeroday_initialtime)
                zeroday_price=[]
                zeroday_price.append({"range": zeroday_range, "lower": zeroday_lower, "upper": zeroday_upper,"time":zeroday_initialtime})
                today_price=[]
                today_price.append({"range": today_range, "lower": today_lower, "upper": today_upper,"time":today_updatetime})

                featureJson = {
                    'CVE_ID': title[8].getText(),
                    'risk': risk,
                    'url': url,
                    'zeroday_price':zeroday_price,
                    'today_price': today_price,
                    'publish_date':zeroday_initialtime
                }
                ES_ip.index(index=esname, doc_type='vuldb', body=featureJson)
                logsFunction.appendWrite('add : '+str(url))

            print(json.dumps(featureJson, indent=2))
            time.sleep(1)
        except Exception as e:
            print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))


@click.command()
@click.option('--es_ip', type=str,default='192.168.163.51')
@click.option('--es_port', type=str, default='59200')
@click.option('--chormdriver_path', type=str)
#120分鐘
def run(es_ip,es_port, chormdriver_path):
    global ES_ip
    ES_ip = Elasticsearch(es_ip+":"+es_port)
    '''log紀錄執行狀況'''
    global logsFunction
    logsFunction = LogsFunc("vuldb")
    get_vuldb(chormdriver_path)


if __name__ == '__main__':
    run()