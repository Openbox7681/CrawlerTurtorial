#!/usr/bin/python
# -*- coding: utf-8 -*-
import requests
from elasticsearch5 import Elasticsearch
from elasticsearch5 import helpers
from bs4 import BeautifulSoup
import geoip2.database
import time
import re
import json

'''取得當下目錄'''
current_path = os.path.abspath(__file__)



def geoip():

        '''取得city mmdb路徑'''
        citymmdb_path=os.path.join(os.path.abspath(os.path.dirname(current_path) + os.path.sep ),'GeoIP2-City.mmdb')

        reader = geoip2.database.Reader(citymmdb_path)
        #reader2 = geoip2.database.Reader('./GeoIP2-ISP.mmdb')

        es = Elasticsearch("211.23.163.51:59200")

        query = {"query": {"bool": {"must_not": {"exists": {"field": "longitude"}}}}}
        #query = {"query": {"bool": {"must_not": [{"exists": {"field": "latitude"}},{"exists": {"field": "longitude"}}]}}}
        #res = es.search(index="info_ptt", doc_type="ptt", body=query, scroll="10m")
        #print("%d ======================>documents found", res['hits']['total'])

        scanResp = helpers.scan(es, query, index='info_ptt', scroll="10m")
        for hit in scanResp:
                #print(hit['_source']['ip'])
                #if response is not None:
                try:
                    if is_valid_ip(hit['_source']['ip']):
                        response = reader.city(hit['_source']['ip'])
                       #  # 有多種語言,我們這裡主要輸出英文和中文
                       #  print("你查詢的IP的地理位置是:================================================")
                       #  print("地區:{}({})".format(response.continent.names["es"], response.continent.names["zh-CN"]))
                       #  print("國家:{}({}) ,簡稱:{}".format(response.country.name, response.country.names["zh-CN"], response.country.iso_code))
                       #  #print("洲/省:{}({})".format(response.subdivisions.most_specific.name, response.subdivisions.most_specific.names["zh-CN"]))
                       #  #print("城市:{}({})".format(response.city.name))
                       #  print("經度:{},緯度{}".format(response.location.longitude, response.location.latitude))
                       #  print("時區:{}".format(response.location.time_zone))
                       #  #print("郵編:{}".format(response.postal.code))
                       #
                       #
                       #print(hit['_id'] + ':' + response.city.names['en'] + ':' + response.country.names['en'])
                        city = str(response.city.names['en'])
                        region = str(response.country.names['en'])
                        requestbody = {"doc": {"city": city, "region": region, "longitude": response.location.longitude, "latitude": response.location.latitude}}
                        es.update(index='info_ptt', doc_type='ptt', id=hit['_id'], body=requestbody)
                except:
                    if is_valid_ip(hit['_source']['ip']):
                        #print('Error address  =============>' + hit['_source']['ip'] + ':' + hit['_id'])
                        time.sleep(10)
                        #response2 = reader2.isp(hit['_source']['ip'])
                        #print(response2)
                        #https://whatismyipaddress.com/ip/220.135.87.177
                        res = requests.get('https://whatismyipaddress.com/ip/'+hit['_source']['ip'])
                        soup = BeautifulSoup(res.text, "lxml")
                        tags = soup.find_all("table", limit=2)
                        tags2 = tags[1].find_all("td")
                        requestbody = prepare_request_body(tags2)
                        es.update(index='info_ptt', doc_type='ptt', id=hit['_id'], body=requestbody)

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
        return {"doc": {"city": city, "region": region, "longitude": float(longitude),
                    "latitude": float(latitude)}}
    elif len(tags2)==4:
        region = tags2[1].text.strip()
        latitude = tags2[2].text.strip('\n')
        longitude = tags2[3].text.strip('\n')
        latitude = latitude[0:latitude.index("(")].strip()
        longitude = longitude[0:longitude.index("(")].strip()
        return {"doc": {"region": region, "longitude": float(longitude),
                    "latitude": float(latitude)}}
    else:

        return ""

if __name__ == "__main__":
    print('Start')
    geoip()

