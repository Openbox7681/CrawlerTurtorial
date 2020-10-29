#!/usr/bin/python
# encoding: utf-8
import re
import requests
import json
import sys
from datetime import datetime
import calendar
import time

from elasticsearch import Elasticsearch
import click
import schedule
from bs4 import BeautifulSoup

from logsContainer_ICSCert import LogsFunc
from slack_alert import AlertFunc


'''找出內文中update紅字，將其刪除'''
def remove_update_tag(string_):
    #<p>開頭
    while string_.find('<p class="red_title"><strong>')>-1:
        start_position=string_.find('<p class="red_title"><strong>')
        end_position=string_.find('</strong></p>')

        string_=string_.replace(string_[(start_position):((end_position)+13)],'')#把<strong>--------- End Update A Part 1 of 1 --------</strong></p>換掉
        start_position=string_.find('<p class="red_title"><strong>')
        end_position=string_.find('</strong></p>')

    #<div>開頭
    while string_.find('<div class="red_title"><strong>')>-1:
        start_position=string_.find('<div class="red_title"><strong>')
        end_position=string_.find('</strong></div>')
        string_=string_.replace(string_[(start_position):((end_position)+15)],'')#把<strong>--------- End Update A Part 1 of 1 --------</strong></p>換掉
        start_position=string_.find('<p class="red_title"><strong>')
        end_position=string_.find('</strong></p>')
    return string_

'''抓取每一篇報告內容'''
def insert(c):
    for id, link, title in c:
        try:
            link = "https://www.us-cert.gov" + link
            res = requests.get(link)
            soup_body = BeautifulSoup(res.text.encode("utf-8"), 'lxml')
            soup = str(BeautifulSoup(res.text.encode("utf-8"), 'lxml')).replace('\n', '').replace('\t', '')
            print(link)

            original_release_date = None
            try:
                original_release_date = str(re.findall('Original release date: (\w* \d*, \d*) ', soup)[0])
                original_release_date = datetime.strptime(original_release_date, '%B %d, %Y')

                #取得資料年份
                year=original_release_date.year
                original_release_date = calendar.timegm(datetime.timetuple(original_release_date)) * 1000
                # print(original_release_date)
                
                #建立es index
                esname = "sec_icscert-"+str(year)
                try:
                    res = ES_ip.indices.create(index=esname)
                    # print(res)
                except Exception as e:
                    # print("Index already exists")
                    pass
            except:
                original_release_date = 'Unknown'

            last_revised = None
            try:
                last_revised = str(
                    re.findall('Last revised: (\w* \d*, \d*)', soup)[0])
                last_revised = datetime.strptime(last_revised, '%B %d, %Y')
                last_revised = calendar.timegm(datetime.timetuple(last_revised)) * 1000
            except:
                last_revised = None

            CVSS = None
            try:
                CVSS = float(re.findall('CVSS [V|v]3 (\d*.\d)', soup)[0])
                # print("CVSS: ",CVSS)
            except:
                CVSS = 'Unknown'
                # print("soup: ",soup)

            attention = None
            try:
                '''ATTENTION'''
                attention = str(re.findall('ATTENTION:(.*?)</li>', soup)[-1])
                #: Low skill level to exploit
                if attention.find(':')>-1:# remove :
                    attention=attention.replace(':', '')
                if attention[0]==(' '):#remove blank
                    attention=attention[(1):(len(attention))]
                if attention.find('\xc2\xa0')>-1:#remove last blank --> unicode \xc2\xa0
                    attention=attention.replace('\xc2\xa0', '')
                error_str = re.findall('<.*?>', attention)
                for j in error_str:
                    # If it is like <em> ,<p> , replace with blank
                    attention = attention.replace(j, '')
            except:                
                    attention = 'Unknown'
                
            vendor = None
            try:
                vendor = str(re.findall('Vendor:(.*?)</li>', soup)[-1])          
                #: Siemens
                if vendor.find(':')>-1:# remove :
                    vendor=vendor.replace(':', '')
                if vendor[0]==(' '):#remove blank
                    vendor=vendor[(1):(len(vendor))]
                if vendor.find('\xc2\xa0')>-1:#remove last blank --> unicode \xc2\xa0
                    vendor=vendor.replace('\xc2\xa0', '')
                error_str = re.findall('<.*?>', vendor)
                for j in error_str:
                    # If it is like <em> ,<p> , replace with blank
                    vendor = vendor.replace(j, '')
            except:
                vendor = 'Unknown'

            equipment = None
            try:
                equipment = str(re.findall('Equipment:(.*?)</li>', soup)[-1])                     
                if equipment.find(':')>-1:# remove :
                    equipment=equipment.replace(':', '')
                if equipment[0]==(' '):#remove blank
                    equipment=equipment[(1):(len(equipment))]
                if equipment.find('\xc2\xa0')>-1:#remove last blank --> unicode \xc2\xa0
                    equipment=equipment.replace('\xc2\xa0', '')
                error_str = re.findall('<.*?>', equipment)
                for j in error_str:
                    # If it is like <em> ,<p> , replace with blank
                    equipment = equipment.replace(j, '')

            except:
                equipment = 'Unknown'
                

            vulnerabilities = None
            try:
                vulnerabilities = str(re.findall('(Vulnerability:|Vulnerabilities:)(.*?)</li>', soup)[-1])                             
                if vulnerabilities.find(':')>-1:# remove :
                    vulnerabilities=vulnerabilities.replace(':', '')
                if vulnerabilities[0]==(' '):#remove blank
                    vulnerabilities=vulnerabilities[(1):(len(vulnerabilities))]
                if vulnerabilities.find('\xc2\xa0')>-1:#remove last blank --> unicode \xc2\xa0
                    vulnerabilities=vulnerabilities.replace('\xc2\xa0', '')
                error_str = re.findall('<.*?>', vulnerabilities)
                for j in error_str:
                    # If it is like <em> ,<p> , replace with blank
                    vulnerabilities = vulnerabilities.replace(j, '')
            except:
                vulnerabilities = 'Unknown'

            risk_evaluation = None
            try:
                risk_evaluation = str(re.findall('RISK EVALUATION<\/h2>.*?<p.*?>(.*?)<\/p>.*?TECHNICAL DETAILS', soup)[0])
                if risk_evaluation.find(':')>-1:# remove :
                    risk_evaluation=risk_evaluation.replace(':', '')
                if risk_evaluation[0]==(' '):#remove blank
                    risk_evaluation=risk_evaluation[(1):(len(risk_evaluation))]
                if risk_evaluation.find('\xc2\xa0')>-1:#remove last blank --> unicode \xc2\xa0
                    risk_evaluation=risk_evaluation.replace('\xc2\xa0', '')
                error_str = re.findall('<.*?>', risk_evaluation)
                for j in error_str:
                    # If it is like <em> ,<p> , replace with blank
                    risk_evaluation = risk_evaluation.replace(j, '')
            except:
                risk_evaluation = 'Unknown'

            affected_products1 = None
            product_version = []
            try:
                affected_products1 = str(
                    re.findall('AFFECTED PRODUCTS<\/h3>(.*)<h.*? VULNERABILITY OVERVIEW', soup))
                #print("affected_products1: ", affected_products1)
                affected_products2 = re.findall('<li>(.*?)<\/li>', affected_products1)                
                if len(affected_products2)==0:
                    affected_products2 = re.findall('<p>(.*?)<\/p>', affected_products1)
                # print('affected_products2: ', affected_products2)
                has_li = False
                for i in range(0, len(affected_products2)):
                    if affected_products2[i].find('<li>') > -1:
                        has_li = True
                # print("has li:",has_li)
                if has_li == True:
                    affected_products3 = re.findall('<li>(.*?)<ul style=.*?">(.*?)<\/ul><\/li>',affected_products1)
                    for j in range(0, len(affected_products3)):
                        '''First class'''
                        # print(affected_products3[j])
                        product = (str(affected_products3[j][0]).replace(':',''))  # SIMATIC WinCC:-->SIMATIC WinCC  remove :
                        # print('affected_products3: ', affected_products3[j])
                        affected_products4 = re.findall('<li>(.*?)<\/li>', affected_products3[j][1])

                        for k in range(0, len(affected_products4)):
                            '''Second class'''
                            # print('Second: ',affected_products4[k])
                            last_char = len(affected_products4[k])-1
                            if affected_products4[k][last_char] == '.' or affected_products4[k][last_char] == ',' or affected_products4[k][last_char] == ':':  # Remove the last .,: of the sentence
                                affected_products4[k] = affected_products4[k][(0):(last_char)]
                            '''combine first and second class'''
                            product_version.append(product + " " + affected_products4[k])
                            # print('product_version: ', product_version)
                    # print("second level : ", affected_products1)
                    rest_data = affected_products1
                    remove_data = str(re.findall('(<ul><li>.*!?<ul\s.*?<\/li><\/ul>)', rest_data)[0])
                    # print("remove",remove_data)
                    rest_data = (rest_data.replace(str(remove_data), ''))
                    # print("rest data")
                    # print(rest_data)
                    rest_data = re.findall('<li>(.*?)<\/li>', rest_data)
                    # print("rest data ==> else product")
                    # print(rest_data)
                    for j in rest_data:
                        last_char = len(j) - 1
                        if j[last_char] == '.':  # Remove the last . of the sentence
                            product_version.append(j[(0):(last_char)])
                        else:
                            product_version.append(j)
                            # print('product_version finish s: ', product_version)
                else:
                    for i in range(0, len(affected_products2)):
                        affected_products2[i] = affected_products2[i].replace(', and', '')
                        affected_products2[i] = affected_products2[i].replace('; and', '')
                        affected_products2[i] = affected_products2[i].replace(' and', '')
                        affected_products2[i] = affected_products2[i].replace(';', '')
                        last_char = len(affected_products2[i]) - 1

                        if affected_products2[i][last_char] == '.' or affected_products2[i][last_char] == ',':  # Remove the last . of the sentence
                            affected_products2[i] = affected_products2[i][(0):(last_char)]
                            product_version.append(str(affected_products2[i]))
                            # print("add : ", affected_products2[i])
                        else:
                            product_version.append(str(affected_products2[i]))
                            # print("add : ",affected_products2[i])
                            # print('product_version finish s: ', product_version)
                # print(product_version)
            except Exception as e:
                print ('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))
                product_version = 'Unknown'

            vulnerability_overview = None
            try:
                vulnerabilityoverview = re.findall('VULNERABILITY OVERVIEW(.*?)(CWE-.*?)<\/a>.*?<p>(.*?)<\/p><p><a href=.*?>(CVE-.*?)<\/a>.*?(\d{1,2}.\d).*?<\/p>',soup)
                #get CWE_title, CWE_ID, description, CVE_ID, score
                vulnerability_overview = []

                for i in range(0, len(vulnerabilityoverview)):
                    try:
                        CWE_title = str(vulnerabilityoverview[i][0]).split('>')[-1]
                        error_str = re.findall('<.*?>', CWE_title)
                        for j in error_str:
                            # If it is like <em> ,<p> , replace with blank
                            CWE_title = CWE_title.replace(j, ' ')
                    except Exception as e:
                        CWE_title = 'Unknown'
                    try:
                        CWE_ID = str(vulnerabilityoverview[i][1])
                        error_str = re.findall('<.*?>', CWE_ID)
                        for j in error_str:
                            # If it is like <em> ,<p> , replace with blank
                            CWE_ID = CWE_ID.replace(j, ' ')
                    except Exception as e:
                        CWE_ID = 'Unknown'
                    try:
                        description = str(vulnerabilityoverview[i][2])                    
                        description = description.replace('</p><p>', ' ')
                        error_str = re.findall('<.*?>', description)
                        for j in error_str:
                            # If it is like <em> ,<p> , replace with blank
                            description = description.replace(j, ' ')
                    except Exception as e:
                        description = 'Unknown'
                    try:
                        CVE_ID = vulnerabilityoverview[i][3]
                        error_str = re.findall('<.*?>', CVE_ID)
                        for j in error_str:
                            # If it is like <em> ,<p> , replace with blank
                            CVE_ID = CVE_ID.replace(j, ' ')
                    except Exception as e:
                        CVE_ID = 'Unknown'
                    try:
                        score = vulnerabilityoverview[i][4]
                        error_str = re.findall('<.*?>', score)
                        for j in error_str:
                            # If it is like <em> ,<p> , replace with blank
                            score = score.replace(j, ' ')
                    except Exception as e:
                        score = 'Unknown'                    

                    vulnerability_overview.append({
                            "CWE_title" :CWE_title,
                            "CWE_ID" :CWE_ID,
                            "description" :description,
                            "CVE_ID" :CVE_ID,
                            "score" :score
                        })                                                                                

            except Exception as e:
                print ('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))
                vulnerability_overview = None

            CVE_ID=[]
            CWE_ID=[]
            for i in vulnerability_overview:
                CVE_ID.append(str(i["CVE_ID"]))
                CWE_ID.append(str(i["CWE_ID"]))

            researcher = None
            try:
                researcher = str(re.findall('RESEARCHER<\/h3><p>(.*?)<\/p>.*?MITIGATIONS', soup)[0])
            except:
                researcher = 'Unknown'

            Critical_Infrastructure_Sector = None

            try:
                for tag in soup_body.find_all("ul"):
                    if tag.find("li") and tag.find("strong") is not None and tag.find("div") is None:
                        li_list = tag.find_all("li")
                Critical_Infrastructure_Sector = li_list[0].getText().split(":")
                #去前後空白
                Critical_Infrastructure_Sector = [item.strip() for item in Critical_Infrastructure_Sector[1].split(",")]
                Critical_Infrastructure_Sector = ",".join(Critical_Infrastructure_Sector)
                if Critical_Infrastructure_Sector.find('\xc2\xa0')>-1:#remove last blank --> unicode \xc2\xa0
                    Critical_Infrastructure_Sector=Critical_Infrastructure_Sector.replace('\xc2\xa0', '')
                if "Financial Services" in Critical_Infrastructure_Sector:
                    print("=================")
                    print(Critical_Infrastructure_Sector)
                # Critical_Infrastructure_Sector = (re.findall('(CRITICAL INFRASTRUCTURE SECTOR.*?|Critical Infrastructure Sector.*?)<\/strong>(.*?)<\/li><li><strong>(COUNTRIES\/AREAS DEPLOYED|Countries\/Areas Deployed)', soup)[0])
                # Critical_Infrastructure_Sector=Critical_Infrastructure_Sector[1]           
                # if attention.find(':')>-1:# remove :
                #     attention=attention.replace(':', '')
                # if Critical_Infrastructure_Sector[0]==(' '):#remove blank
                #     Critical_Infrastructure_Sector=Critical_Infrastructure_Sector[(1):(len(Critical_Infrastructure_Sector))]
                # if Critical_Infrastructure_Sector.find('\xc2\xa0')>-1:#remove last blank --> unicode \xc2\xa0
                #     Critical_Infrastructure_Sector=Critical_Infrastructure_Sector.replace('\xc2\xa0', '')
                
            except:
                Critical_Infrastructure_Sector = 'Unknown'

            Countries_Areas_Deployed = None
            try:
                Countries_Areas_Deployed = (re.findall(
                    '(COUNTRIES\/AREAS DEPLOYED|Countries\/Areas Deployed):.*?<\/strong>(.*?)<\/li><li',
                    soup)[0])
                Countries_Areas_Deployed=Countries_Areas_Deployed[1]

                if Countries_Areas_Deployed[0]==(' '):#remove blank
                    Countries_Areas_Deployed=Countries_Areas_Deployed[(1):(len(Countries_Areas_Deployed))]

                if Countries_Areas_Deployed.find('\xc2\xa0')>-1:#remove last blank --> unicode \xc2\xa0
                    Countries_Areas_Deployed=Countries_Areas_Deployed.replace('\xc2\xa0', '')
            except:
                Countries_Areas_Deployed = 'Unknown'
            
            Company_Headquarters_Location = None
            try:
                Company_Headquarters_Location = (re.findall(
                    '(COMPANY HEADQUARTERS LOCATION|Company Headquarters Location):.*?<\/strong>(.*?)<\/li><\/ul>',
                    soup)[0])
                Company_Headquarters_Location=Company_Headquarters_Location[1]

                if Company_Headquarters_Location[0]==(' '):#remove blank
                    Company_Headquarters_Location=Company_Headquarters_Location[(1):(len(Company_Headquarters_Location))]

                if Company_Headquarters_Location.find('\xc2\xa0')>-1:#remove last blank --> unicode \xc2\xa0
                    Company_Headquarters_Location=Company_Headquarters_Location.replace('\xc2\xa0', '')
            except:
                Countries_Areas_Deployed = 'Unknown'
            
            background = []
            background.append(
                {"Critical_Infrastructure_Sectors": Critical_Infrastructure_Sector,
                "Countries_Areas_Deployed": Countries_Areas_Deployed,
                "Company_Headquarters_Location": Company_Headquarters_Location
                })
                    
            existence_of_exploit=None
            try:
                '''先從attention裡面找'''
                attention_= attention+str('/')# inorder to search like :Exploitable from the same local network segment (OSI Layer 2)
                attention_lower=attention_.lower()

                if ((attention_lower.find('public exploits are available')))>-1:
                    existence_of_exploit='Public exploits are available.'
                elif attention_lower.find('/')>-1:
                    existence_of_exploit = str(re.findall('\/(.*?targets [this vulnerability|these vulnerabilities].*?)\/', attention_)[0])                   
            except Exception as e:
                try:    
                    '''在attention裡面找不到，找全文'''
                    '''第一種'''
                    existence_of_exploit = str(re.findall('((No known|Known) public exploits specifically target (this.*?vulnerability|these vulnerabilities).)', soup)[0][0])
                except:
                    try:
                        '''第二種'''
                        existence_of_exploit = str(re.findall('(Exploits.*?target.*?[this vulnerability|these vulnerabilities].*?\.)', soup)[0])
                    except:
                        existence_of_exploit='Unknown'
            
            exploitability=None
            try:
                '''先從attention裡面找'''
                attention_= attention+str('/')
                attention_lower=attention_.lower()
                if attention_lower.find('/')>-1:
                    exploitability = str(re.findall('(.*?xploitable.*?)\/', attention_)[0])
                elif((attention_lower=='exploitable remotely')or(attention_lower=='exploitable remotely.')):
                    exploitability='Exploitable remotely'
                # else:         
            except Exception as e:
                try:    
                    '''在attention裡面找不到，找全文'''
                    exploitability = str(re.findall('(This vulnerability is.*?\.)', soup)[0])
                except:
                    try:
                        '''These vulnerabilities are開頭的'''
                        exploitability = str(re.findall('(These vulnerabilities are.*?\.)', soup)[0])
                    except:
                        try:
                            '''These vulnerabilities is開頭的'''
                            exploitability = str(re.findall('(These vulnerabilities is.*?\.)', soup)[0])
                            exploitability=exploitability.replace('These vulnerabilities is','These vulnerabilities are')
                        except:
                            exploitability='Unknown'

            difficulty=None
            try:
                difficulty = str(re.findall('((High|high|Low|low|Moderate|moderate) skill level.*?exploit)', soup)[0][0])                    
            except Exception as e:
                difficulty = 'Unknown'

            vendor_mitigation_html=None
            try:
                '''第一種'''
                vendor_mitigation_html = str(re.findall('MITIGATIONS<\/h2>(.*?)<p>NCCIC recommends', soup)[0])
                vendor_mitigation_html=remove_update_tag(vendor_mitigation_html)      
            except Exception as e:
                try:
                    '''第二種'''
                    vendor_mitigation_html = str(re.findall('MITIGATIONS<\/h2>(.*?)<p>NCCIC reminds organizations', soup)[0])
                except Exception as e:
                    vendor_mitigation_html = 'Unknown'
                            
            vendor_mitigation=vendor_mitigation_html
            try:
                '''找出html tag，並移除'''
                error_tags = re.findall('<.*?>', vendor_mitigation)
                
                for error_tag in error_tags:
                    vendor_mitigation = vendor_mitigation.replace((error_tag), '')                            
            except Exception as e:
                vendor_mitigation = 'Unknown'

            NCCIC_mitigation_html=''
            try:
                NCCIC_mitigation_html = str(re.findall('(<p>NCCIC.*?recommends.*?)<p>NCCIC reminds organizations to perform proper impact analysis and risk assessment prior to deploying defensive measures', soup)[0])
                NCCIC_mitigation_html=remove_update_tag(NCCIC_mitigation_html)   
            except Exception as e:
                NCCIC_mitigation_html = ''
            
            NCCIC_mitigation=NCCIC_mitigation_html
            try:
                '''找出html tag，並移除'''
                error_tags = re.findall('<.*?>', NCCIC_mitigation)
                for error_tag in error_tags:
                    NCCIC_mitigation = NCCIC_mitigation.replace(error_tag, '')                        
            except Exception as e:
                NCCIC_mitigation = ''

            featureJson = {
                "url": link,
                "id": id,
                "title": title,
                "publish_date": original_release_date,
                "update_date": last_revised,
                "CVSS_V3": CVSS,
                "attention": attention,
                "vendor": vendor,
                "equipment": equipment,
                'vultype':vulnerabilities,
                "content":risk_evaluation,
                "product": product_version,
                "vulnerability_overview": vulnerability_overview,
                "researcher": researcher,
                "background": background,
                "NCCIC_mitigation":NCCIC_mitigation,
                "vendor_mitigation":vendor_mitigation,
                "NCCIC_mitigation_html":NCCIC_mitigation_html,
                "vendor_mitigation_html":vendor_mitigation_html,
                "existence_of_exploit":existence_of_exploit,
                "difficulty":difficulty,
                "exploitability":exploitability,
                'cve_id':(CVE_ID),
                'cwe_id':(CWE_ID),
                'category':Critical_Infrastructure_Sector
            }
            if "Financial Services" in  featureJson["background"][0]["Critical_Infrastructure_Sectors"]:
                print(json.dumps(featureJson["background"][0]["Critical_Infrastructure_Sectors"], indent=2))
            # print((featureJson.values()))

            '''檢查欄位有無缺漏，缺漏不新增，除了更新日期，可以新增則allcorrect為True'''
            logsFunction = LogsFunc("ICSCert")
            allcorrect=True
            logsFunction.appendWriteError('start: '+(id)+'---')
            error_column=[]

            for key,value in featureJson.items():
                if len(featureJson["product"])>0 and len(featureJson["vulnerability_overview"])>0:
                    if str(value) == "None":
                        if str(key) == "update_date":#沒有更新日期可以略過
                            # print("update_date is null")    
                            pass                
                        else:
                            print('error column : ',key)
                            '''record error column'''
                            allcorrect=False
                            error_column.append(key)

            if len(featureJson["product"])<=0:#產品跟漏洞資訊空的，也不能新增
                print('error column : product')
                allcorrect=False
                error_column.append('product')
            if len(featureJson["vulnerability_overview"])<=0:#產品跟漏洞資訊空的，也不能新增
                print('error column : vulnerability_overview')
                allcorrect=False
                error_column.append('vulnerability_overview')

            '''新增與更新'''
            if allcorrect==True:
                query = {
                    "query": {
                        "bool": {
                            "must": [
                                {
                                    "query_string": {
                                        "default_field": "id.keyword",
                                        "query": "id:\"" + str(id) + "\""
                                    }
                                }
                            ]
                        }
                    }
                }

                response = ES_ip.search(index=esname, body=query)
                # print('len: ',len(response["hits"]["hits"]))
              
                if len(response["hits"]["hits"]) > 0:#更新
                    print((response["hits"]["hits"][0]["_source"]["id"]),'in es',id,' updating...')
                    ES_ip.index(index=esname, doc_type='ics', body=featureJson,id=response["hits"]["hits"][0]["_id"])
                    logsFunction.appendWriteError('update '+str(id))
                else:#新增
                    logsFunction.appendWrite(str(featureJson),id)
                    print('add... ')
                    ES_ip.index(index=esname, doc_type='ics', body=featureJson)
                    logsFunction.appendWriteError('add '+str(id))

                    '''alert to slack'''    
                    t = datetime.now()
                    AlertFunction = AlertFunc()
                    text=str(t)+(' add ：')+id
                    AlertFunction.alert_to_slack(text)
                    
            else:#allcorrect==FALSE
                query = {
                    "query": {
                        "bool": {
                            "must": [
                                {
                                    "query_string": {
                                        "default_field": "id.keyword",
                                        "query": "id:\"" + str(id) + "\""
                                    }
                                }
                            ]
                        }
                    }
                }

                response = ES_ip.search(index=esname, body=query)
                # print('len: ',len(response["hits"]["hits"]))
              
                if len(response["hits"]["hits"]) < 1:#沒有在es裡，而且欄位有錯誤，需要人工新增，加入log以及slack提醒
                    logsFunction.appendWrite(str(featureJson),id)
                    '''alert to slack'''    
                    AlertFunction = AlertFunc()
                    text=id+(' error column: ')+str(error_column)
                    AlertFunction.alert_to_slack(text)
                    logsFunction.appendWriteError((text))
        except Exception as e:
            print('error link', link)
            logsFunction.appendWriteError(('error link'+link))

'''進入每一頁，取得ICSCert id, link, title'''
def web_pages(u):
    res = requests.get(u)
    soup = str(BeautifulSoup(res.text.encode("utf-8")))
    # print(soup)
    string = '<span class="field-content">(.*?)<\/span>\s*<\/span>\s*.*?\s*<span class="views-field views-field-title">\s*<span class="field-content"><a href="(.*?)" hreflang="en">(.*?)<\/a><\/span>\s*<\/span>'
    each_url_data = re.findall(string, soup)
    # print(len(each_url_data))
    insert(each_url_data)    


def getICSCert():
    '''crawler the count of the page'''
    for i in range(0, 50):
        # web_link = 'https://ics-cert.us-cert.gov/advisories?page=' + str(i)
        web_link = 'https://www.us-cert.gov/ics/advisories?page=' + str(i)
        print("---------------")
        print(web_link)
        web_pages(web_link)

@click.command()
@click.option('--es_ip', type=str,default='211.23.163.51')
@click.option('--es_port', type=str, default='59200')
#360分鐘執行一次
def run(es_ip,es_port):
    global ES_ip
    ES_ip = Elasticsearch(es_ip+":"+es_port)
    '''log紀錄執行狀況'''
    global logsFunction
    logsFunction = LogsFunc("ICSCert")
    getICSCert()


if __name__ == '__main__':
    run()
