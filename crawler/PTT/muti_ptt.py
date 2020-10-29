#!/usr/bin/python
# vim: set fileencoding:utf-8
# update
from flask import Flask, request
import psutil
import requests
import re
import urllib
import sys
import datetime
import time
import os
# import pymysql
import conf
import multiprocessing
import geoip2.database
from bs4 import BeautifulSoup
import datetime
from datetime import timedelta
import pytz
import json
import click
import jieba
import jieba.analyse

jieba.set_dictionary('extra_dict/dict.txt.big')
jieba.load_userdict('user.dict')
# update
app = Flask(__name__)
process = []
flask_init = conf.flask_init

es = conf.es
mysql_init = conf.mysql_init
ptt = "https://www.ptt.cc"




def get_news_content(link, html, bbs_name):
    soup = BeautifulSoup(html, features="html.parser")
    meta = soup.find_all('span', class_="article-meta-value")
    try:
        author = meta[0].text
        title = meta[2].text
        time = meta[3].text
    except:
        return None
    txt = soup.find('div', id="main-content")
    f2 = soup.find_all('span', class_="f2")
    cut_link = ""

    for i in f2:
        if "來自" in i.text:
            cut_ip = i.getText().split(",")[-1]
            try:
                pattern = " 來自: ([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}).*$"
                ip = re.findall(pattern,cut_ip)[0]
            except Exception as e:
                print("Ip is suspend")
                ip = None
                print(e)      
        if link in i.text:
            cut_link = i.text
            break
    txt_next = txt.text.split(meta[3].text)
    try:
        txt_final = txt_next[1].split(cut_link)
        cont = txt_final[0]
        # print("Cont : ")
        # print(cont)
        datetime_object = datetime.datetime.strptime(
            time, '%a %b %d %H:%M:%S %Y')
        board = link.split("/")[2]
        region_json = None
        region_json = get_ip_info(ip)
        try:
            region = region_json["region"]
            city = region_json["city"]
            longitude = region_json["longitude"]
            latitude = region_json["latitude"]
        except Exception as e:
            region = None
            city = None
            longitude = None
            latitude = None
        jiebakeyword = jieba_keyword(cont)
        news = {
            'BBS': bbs_name,
            'Title': title,
            'URL': link,
            'Date': datetime_object,
            "PublishTime" : int(datetime_object.timestamp()) *1000,
            'Author': author,
            'Description': cont,
            'Board': board,
            'Type' : "content",
            "Ip" : ip,
            "Region" : region,
            "City" : city,
            "longitude" : longitude, 
            "latitude" : latitude,
            "JiebaKeyword" : jiebakeyword
        }
        return news

    except Exception as e:
        print(e)
        return None


def get_news_comments(title, link, html, bbs_name):
    comments = list()
    soup = BeautifulSoup(html, features="html.parser")
    meta = soup.find_all('span', class_="article-meta-value")
    try:
        year = meta[3].text.split(" ")[-1]
    except Exception as e :
        print(e)
        year = "2019"
    push = soup.find_all('div', class_="push")
    floor = 1
    pushCount = 0
    pullCount = 0
    for i in push:
        try:
            try:
                author = i.find_all("span")[1].getText()
            except Exception as e:
                author = None
            req = i.text
            try:
                local = i.find("span", class_="push-ipdatetime")
                local = local.getText().split(" ")
                ip = local[len(local)-3]
            except Exception as e :
                ip = None
                print(e)
            req_list = req.split(" ")

            try:
                message = i.find_all("span")[2].getText().replace(":","").strip()
            except Exception as e:
                message = req.split(":")[1].split(" ")
                message = " ".join(i for i in message[:-3])
            req_time = year + " " + req[-12:]
            if "protected" in req:
                continue
            req_time = req_time.strip()
            reqtime_object = datetime.datetime.strptime(req_time, "%Y %m/%d %H:%M")
            board = link.split("/")[2]
            region_json = None
            region_json = get_ip_info(ip)
            try:
                region = region_json["region"]
                city = region_json["city"]
                longitude = region_json["longitude"]
                latitude = region_json["latitude"]
            except Exception as e:
                region = None
                city = None
                longitude = None
                latitude = None
            jiebakeyword = jieba_keyword(message)
            if "推" in req_list[0]:
                pushCount+=1
            if "噓" in req_list[0]:
                pullCount+=1
            doc_push = {
                'Floor': floor,
                'Title': title,
                'BBS': bbs_name,
                'Push': req_list[0],
                'URL': link,
                'Board': board,
                'Author': author,
                'Message': message,
                'Date': reqtime_object,
                "PublishTime" : int(reqtime_object.timestamp()) *1000,
                'Req': req,
                'Ip':ip,
                'Type' : "req",
                "Region" : region,
                "City" : city,
                "longitude" :longitude,
                "latitude" : latitude,
                "JiebaKeyword":jiebakeyword
            }
            floor += 1
            comments.append(doc_push)
        except Exception as e:
            # print('Error: ' + str(e))
            continue
    return comments, pushCount, pullCount


def get_previous_page_link(bbs_URL, s):
    try:
        r = s.get(bbs_URL)
        soup = BeautifulSoup(r.text, features="html.parser")
        btn = soup.find_all('a', class_="btn wide")
        return "https://www.ptt.cc" + btn[1]['href']
    except:
        return None


def get_last_newsdatetime_from_es():
    # 從Elasticsearch中取得最新一筆的新聞時間，最後會將這筆新聞時間更新到 MySQL中
    utc = pytz.UTC
    now = utc.localize(datetime.datetime.now())
    res = es.search(index="sec_ptt-*", doc_type='ptt',
                    body={
                        "aggs":
                          {
                              "max_datetime":
                              {
                                  "max":
                                  {
                                      "field": "Date"}
                              }
                          },
                        "query":
                        {
                              "range":
                                  {
                                      "Date":
                                      {
                                          "lte": now
                                      }
                                  }
                          }

                    }
                    )
    timestamp = res['aggregations']['max_datetime']['value']
    lastnews = datetime.datetime.fromtimestamp(timestamp/1000, tz=pytz.utc)
    return lastnews


def update_last_news_datetime(bbs_id, now_pagenum):
    # 從Elasticsearch中取得最新一筆的新聞時間，最後會將這筆新聞時間更新到 MySQL
    lastnewsdatetime = get_last_newsdatetime_from_es()
    db = pymysql.connect(host = mysql_init.ip, port=mysql_init.port,  user= mysql_init.user,
                         passwd = mysql_init.password, db = "SecBuzzersV2", charset='utf8')
    update = "UPDATE ptt_list set lastnewsdatetime= '%s', lastpagenum= '%s' WHERE id = %s" % (
        str(lastnewsdatetime)[0:19], now_pagenum, bbs_id)
    query = db.cursor()
    query.execute(update)
    db.commit()


@app.route("/process/start")
def start():
    global process
    if len(process) == 0:
        p = mp.Process(target=main)
        p.start()
        p.join(timeout=0.2)
        process.append(p)
        return conf.error_define(True, "Start")
    else:
        for i in process:
            parent = psutil.Process(i.pid)
            conf.kill_process(parent)
        process = []
        return conf.error_define(True, "Empty")

# update
@app.route("/process/check")
def check():
    global process
    return conf.error_define(True, len(process))


def saveES(esindex, docid, doc):
    res = es.index(index=esindex, doc_type="ptt", id=docid, body=doc,request_timeout = 600)


def get_links_from_index(page):

    soup = BeautifulSoup(page, features="html.parser")
    divs = soup.find_all('div', class_='r-ent')
    linkList = list()
    for div in divs:
        soup_title = BeautifulSoup(str(div), features="html.parser")
        title = soup_title.find_all('div', class_='title')
        news_title = title[0].text.strip()
        try:
            link = title[0].find('a')['href'].strip()
        except:
            continue
        if '[公告]' in news_title or '[協尋]' in news_title:
            continue
        linkList.append([news_title, link])

    # 因為每一個 index.html中的文章，最新的那篇是在最底下，所以做個 reversed
    # 這樣最新的文章就會是在 linkList[0]
    linkList = reversed(linkList)
    return linkList


def collect_index(bbs_name, bbs_URL, s, page, lastnewsdatetime, lastpagenum):

    # 一個 index.html會有很多篇新聞
    # 先用BeautifulSoup
    # 蒐集每個Link的 文章內容＋留言
    linkList = get_links_from_index(page)
    for title, link in linkList:
        pushCount = 0
        pullCount = 0
        while True:
            try:
                html = s.get(ptt + link).text
                break
            except Exception as e:
                html = s.get(ptt + link).text
        content = get_news_content(link, html, bbs_name)
        comments, pushCount, pullCount= get_news_comments(title, link, html, bbs_name)
        if content is not None:
            content['Pushcount'] = pushCount
            content['Pullcount'] = pullCount

        # 蒐集失敗
        if content == None or comments == None:
            print("Parsing failed in %s , %s" % (title, link))
            continue
        # Compare
        now_newsdatetime = content['Date']



        
        now_pagenum = ''.join(filter(str.isdigit, bbs_URL))
        print("現在爬到的時間是 %s , 上次爬的時間是 %s " % (now_newsdatetime, lastnewsdatetime))

        if now_newsdatetime < lastnewsdatetime:
            return True

        # if int(now_pagenum) < int(lastpagenum):
        #     return True

        print("%s \t %s" % (str(content['Date']), title))


        year = now_newsdatetime.year
        month = now_newsdatetime.month

        esname = "{}-{}{}{}".format("sec_ptt", str(year), "0" if month < 10 else "", str(month))
        # 儲存 文章和留言到ES中
        # 指定es的 doc id , 這樣重複儲存時就會覆蓋掉原本的

        doc_id1 = content['Board']+"-" + str(content['Date'])+"-"+content['Author']
        saveES(esname, doc_id1, content)
        for comment in comments:
            pttId = comment["URL"].split("/")[-1]
            doc_id2 = pttId+"-" + \
                str(comment['Floor'])+"-"+comment['Author']
            saveES(esname, doc_id2, comment)

    return False


def get_region(ip):
    try:
        region_link = region_url + ip
        s = requests.Session()
        region_json = s.get(region_link).json()
        return region_json
    except Exception as e:
        print("此IP找不到對應國家，請更新資料庫")
        return None

def get_all_index_url(bbs_URL):

    indexList = list()
    try:
        s = requests.Session()
        s.post(ptt + "/ask/over18", data={'yes': 'yes'})
        pre_page_url = get_previous_page_link(bbs_URL, s)
        max_page_number = int(pre_page_url.split(
            "/")[-1].replace("index", "").replace(".html", ""))
        max_page_number += 1   # 加上1才會取得首頁的流水號

        for i in range(1, max_page_number):  # 使用首頁流水號，取得所有index的url
            index = "index%s.html" % (str(i))
            words = bbs_URL.split("/")
            words[-1] = index
            url = "/".join(words)
            indexList.append(url)
        result = reversed(indexList)

        return result

    except:
        print("Start collecting board failed.")
        return indexList


def collect_board(bbs_id, bbs_name, bbs_URL, state, lastnewsdatetime, lastpagenum):

    urls = get_all_index_url(bbs_URL)
    num = 0
    pagenum = 1

    for url in urls:

        num = num + 1
        # 第一次連到網頁時，會詢問你是否 18歲
        s = requests.Session()
        s.post(ptt + "/ask/over18", data={'yes': 'yes'})
        page = s.get(url).text
        print("\n%s" % (url))
        isFinished = collect_index(
            bbs_name, url, s, page, lastnewsdatetime, lastpagenum)  # 爬取一頁index.html的資料
        if num == 1:
            pagenum = "".join(filter(str.isdigit, url))
            # True: 本次蒐集的新聞已經搜集完畢了
            # False：還有下一頁的index.html要蒐集
        if isFinished:
            # update_last_news_datetime(bbs_id, pagenum)  # 更新最新的news日期到 MySQL中
            break
        else:
            # collect_index()只會爬取一個 index.html
            # 當爬取完一個index.html，則要透過 get_previous_page_link()函式，獲得下一個 index.html
            # 取得'上頁'的連結 , /xxx/index{num}.html
            pre_page = get_previous_page_link(bbs_URL, s)

            # 如果爬取到這個看版的最後一頁（index1.html），則結束爬蟲
        if pre_page == None or "index1.html" in bbs_URL:  # collected all, then break out.
            # update_last_news_datetime(bbs_id, pagenum)  # 更新最新的news日期到 MySQL中
            break

def get_ip_info(ip):
    '''取得當下目錄'''
    current_path = os.path.abspath(__file__)
    '''取得city mmdb路徑'''
    citymmdb_path=os.path.join(os.path.abspath(os.path.dirname(current_path) + os.path.sep ),'GeoIP2-City.mmdb')

    reader = geoip2.database.Reader(citymmdb_path)
    try:
        if is_valid_ip(ip):
            response = reader.city(ip)
            city = str(response.city.names['en'])
            region = str(response.country.names['en'])
            requestbody = {"city": city, "region": region, "longitude": response.location.longitude, "latitude": response.location.latitude}
            return requestbody
        else:
            return None
    except:
        if is_valid_ip(ip):
            res = requests.get('https://whatismyipaddress.com/ip/'+ip)
            soup = BeautifulSoup(res.text, "lxml")
            tags = soup.find_all("table", limit=2)
            tags2 = tags[1].find_all("td")
            requestbody = prepare_request_body(tags2)
            return requestbody
def is_valid_ip(ip):
    if ip is not None:
        m = re.match(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$", ip)
        return bool(m) and all(map(lambda n: 0 <= int(n) <= 255, m.groups()))

def prepare_request_body(tags2):
    if len(tags2)==5:
        region = tags2[1].text.strip()
        city = tags2[2].text.strip()
        latitude = tags2[4].text.strip('\n')
        longitude = tags2[5].text.strip('\n')
        latitude = latitude[0:latitude.index("(")].strip()
        longitude = longitude[0:longitude.index("(")].strip()
        return {"city": city, "region": region, "longitude": float(longitude),
                    "latitude": float(latitude)}
    elif len(tags2)==4:
        region = tags2[1].text.strip()
        latitude = tags2[2].text.strip('\n')
        longitude = tags2[3].text.strip('\n')
        latitude = latitude[0:latitude.index("(")].strip()
        longitude = longitude[0:longitude.index("(")].strip()
        return {"region": region, "longitude": float(longitude),
                    "latitude": float(latitude)}
    else:
        return None

def jieba_sentance(sentence):
        seg_list = jieba.cut(sentence, cut_all=False)
        return seg_list
def jieba_keyword(sentence):
    remove_pattern = ["https" , "com" , "udn" , "news", "imgur","jpg","--","cc","ptt"]
    result = list()
    for x ,w in jieba.analyse.extract_tags(sentence, withWeight=True):
        if x not in remove_pattern:
            result.append(x)
    for x ,w in jieba.analyse.textrank(sentence, withWeight=True):
        if x not in result and x not in remove_pattern:
            result.append(x)
    return result

def TF_IDF(sentence):
    #基于 TF-IDF 算法的关键词抽取
    #jieba.analyse.set_idf_path('extra_dict/idf.txt.big')
    result = dict()
    for x, w in jieba.analyse.extract_tags(sentence, withWeight=True):
        result[x] = w
    return result
def TextRank(sentence):
    #基于 TextRank 算法的关键词抽取
    result = dict()
    for x, w in jieba.analyse.textrank(sentence, withWeight=True):
        result[x] = w
    return result           

@click.command()
@click.option('--bbs_id', type=str, default='1')
@click.option('--bbs_name', type=str, default='八卦')
@click.option('--bbs_url', type=str, default='https://www.ptt.cc/bbs/Gossiping/index.html')
@click.option('--status', type=str, default='1')
@click.option('--lastnewsdatetime', type=str, default='2016-06-22 11:18:53')
@click.option('--lastpagenum', type=str, default='1')
@click.option('--duration_day', type = int ,default=1)

def main(bbs_id, bbs_name, bbs_url, status, lastnewsdatetime, lastpagenum , duration_day):

    while True:


        now = datetime.datetime.now()
        lastnewsdatetime = now - timedelta(days=duration_day)
        # lastnewsdatetime = datetime.datetime.strptime(lastnewsdatetime, "%Y-%m-%d %H:%M:%S")



        print("========")

        collect_board( bbs_id, bbs_name,bbs_url,status , lastnewsdatetime, lastpagenum)
        p = multiprocessing.Process(target=collect_board, args=[
                                    bbs_id, bbs_name, bbs_url, status, lastnewsdatetime, lastpagenum])
        p.start()
        p.join()

        print("========")


        # db = pymysql.connect(host = mysql_init.ip, port=mysql_init.port,  user= mysql_init.user,
        #                  passwd = mysql_init.password, db = "SecBuzzersV2", charset='utf8')
        # sql = "Select * from ptt_list"
        # query = db.cursor()
        # query.execute(sql)
        # result = query.fetchall()
        # list_id = []

        # 從資料庫中取得每一個版，並且爬每一個版
        # for row in result:
        #     bbs_id = row[0]
        #     bbs_name = row[1]
        #     bbs_URL = row[2]
        #     state = row[3]
        #     lastnewstime = row[4]
        #     print(type(lastnewstime))
        #     lastpagenum = row[5]
        #     print("Start collecting for ", bbs_name, lastnewstime)
        #     print(bbs_id)
        #     print(bbs_name)
        #     print(bbs_URL)
        #     print(state)
        #     print(lastnewstime)
        #     print(lastpagenum)

        #     collect_board( bbs_id, bbs_name,bbs_URL,state , lastnewstime)
        #     p = multiprocessing.Process(target=collect_board, args=[
        #                                 bbs_id, bbs_name, bbs_URL, state, lastnewstime, lastpagenum])
        #     p.start()
        #     p.join()

        print("sleep...")
        time.sleep(int(10))
        break

if __name__ == "__main__":
        #app.run(host = flask_init.ip ,port = 5300)
    main()
    # print get_last_newsdatetime_from_es()
