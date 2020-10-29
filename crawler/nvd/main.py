#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import requests
from datetime import datetime
import calendar
import sys
import json
import lxml
import click
import schedule
from elasticsearch import Elasticsearch
from bs4 import BeautifulSoup

from logContainer import LogsFunc

'''新增每一筆cve id 的資料'''
def insert(match,esname):
    for i in range(0, len(match)):
        # print(match[i][1])
        query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "query_string": {
                                "default_field": "nvd.CVE_ID",
                                "query": "CVE_ID:\"" + str(match[i][1]) + "\""
                            }
                        }
                    ]
                }
            }
        }

        response = ES_ip.search(index=esname,doc_type="nvd", body=query)
        featureJson={}
        try:
            url = 'https://cve.mitre.org/cgi-bin/cvename.cgi?name=' + \
                str(match[i][0])
            res = requests.get(url)

            soup = str(BeautifulSoup(res.text,"lxml"))

            DateEntryCreated = None
            try:
                string = '<th colspan="2">Date Entry Created<\/th>\s*<\/tr>\s*<tr>\s*<td><b>(\d*)<\/b><\/td>'
                DateEntryCreated = str(re.findall(string, soup)[0])
                DateEntryCreated = datetime.strptime(
                    DateEntryCreated, '%Y%m%d')
                DateEntryCreated = calendar.timegm(
                    datetime.timetuple(DateEntryCreated)) * 1000
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            url = 'https://nvd.nist.gov' + str(match[i][0])
            res = requests.get(url)
            #                      print match[i][j]
            soup = (BeautifulSoup(res.text,"lxml"))
            # print soup

            PatchDate=None
            try:
                ChangeHistory=str(soup.find('div',{'id':'p_lt_WebPartZone1_zoneCenter_pageplaceholder_p_lt_WebPartZone1_zoneCenter_VulnerabilityDetail_VulnFormView_VulnChangeHistoryDiv'}))
                string='(\d*\/\d*\/\d{4})[\s\S]*?Patch'
                PatchDate = str(re.findall(string, ChangeHistory)[0]) 
                # print(PatchDate)
                PatchDate = datetime.strptime(PatchDate, '%m/%d/%Y')
                PatchDate = calendar.timegm(datetime.timetuple(PatchDate)) * 1000
                # print(PatchDate)
            except:
                PatchDate=None


            OriginalReleaseDate = None
            try:

                string = '<strong>NVD Last Modified:<\/strong><br\/>\s*<span data-testid="vuln-last-modified-on">(.*?)<\/span><br\/>'



                OriginalReleaseDate = soup.find("span", {"data-testid" : "vuln-published-on"}).getText()  # 02/01/2018

                OriginalReleaseDate = datetime.strptime(
                    OriginalReleaseDate, '%m/%d/%Y')
                OriginalReleaseDate = calendar.timegm(
                    datetime.timetuple(OriginalReleaseDate)) * 1000
                #                     	print OriginalReleaseDate
            except Exception as e:
                pass
                print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))


            soup = str(soup)
            LasTrevised = None
            try:
                string = '<strong>NVD Last Modified:<\/strong><br\/>\s*<span data-testid="vuln-last-modified-on">(.*?)<\/span><br\/>'
                LasTrevised = str(re.findall(
                    string, soup)[0])  # 02/21/2018

                LasTrevised = datetime.strptime(
                    LasTrevised, '%m/%d/%Y')
                LasTrevised = calendar.timegm(
                    datetime.timetuple(LasTrevised)) * 1000
                #                     	print LasTrevised
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            Overview = None
            try:
                string = '<h3 id="vuln.*?" data-testid="vuln-description-title">.*?Description<\/h3>\s*<p data-testid="vuln-description">(.*?)<\/p>'
                Overview = str(re.findall(string, soup)[0])
                #                     	print Overview
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            CWE = None
            try:
                string = '<li data-testid="vuln-technical-details-0-link">.*?\(<a href=".*?" target="_blank">(.*?CWE-.*?)<\/a>\)<\/li>'
                CWE = str(re.findall(string, soup)[0])
                #                    	 print CWE
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            References_all = None
            try:
                # <td data-testid="vuln-hyperlinks-restype-2">([\s\S]*)<\/td>\s*<\/tr>\s*<\/tbody>\s*<\/table>
                # \s*<\/div>\s*<div .*?\s*<h3>Technical Details<\/h3>
                # <td data-testid="vuln-hyperlinks-restype-0">([\s\S]*)<\/td>\s*<\/tr>\s*<tr data-testid="vuln-hyperlinks-row-1">
                string = '<tr data-testid="vuln-hyperlinks-row-\d">\s*<td data-testid="vuln-hyperlinks-link-\d">.*?>(.*?)<\/a><\/td>'
                hyperlinks = re.findall(string, soup)
                # print 'hyperlinks',hyperlinks
                string = '(<td data-testid="vuln-hyperlinks-restype-\d">(\s*.*?\s*)*<\/td>)'
                resource = re.findall(string, soup)
                # print 'resource',resource

                References_all = []
                for link_ in range(0, len(hyperlinks)):
                    # print(hyperlinks[i])
                    string = '<span class="badge">(.*?)<\/span>'
                    each_resource = re.findall(
                        string, str(resource[link_]))  # list
                    # print(each_resource)
                    References_all.append(
                        {"Hyperlink": str(hyperlinks[link_]), "Resource": each_resource})
                    # print('-----')

                # print(References_all)
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            CVSSv3BaseScore = None
            try:
                string = '<span data-testid="vuln-cvssv3-base-score">(.*?) <\/span>'
                CVSSv3BaseScore = float(
                    re.findall(string, soup)[0])  # 9.8
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            ImpactScore = None
            try:
                string = '<strong>Impact Score:\s*<\/strong>\s*<span data-testid="vuln-cvssv3-impact-score">\s*(.*?)\s*<\/span>'
                ImpactScore = float(re.findall(string, soup)[0])  # 1.4
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            ExploitabilityScore = None
            try:
                string = '<strong>Exploitability Score:\s*<\/strong>\s*<span data-testid="vuln-cvssv3-exploitability-score">\s*(.*?)\s*<\/span>'
                ExploitabilityScore = float(
                    re.findall(string, soup)[0])  # 3.9
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            AttackVector = None
            try:
                string = '<strong>Attack Vector \(AV\):\s*<\/strong>\s*<span data-testid="vuln-cvssv3-av">\s*(.*?)\s*<\/span>'
                AttackVector = str(re.findall(
                    string, soup)[0])  # Network
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            AttackComplexity = None
            try:
                string = '<strong>Attack Complexity \(AC\):\s*<\/strong>\s*<span data-testid="vuln-cvssv3-ac">\s*(.*?)\s*<\/span>'
                AttackComplexity = str(
                    re.findall(string, soup)[0])  # Low
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            PrivilegesRequired = None
            try:
                string = '<strong>Privileges Required \(PR\):\s*<\/strong>\s*<span data-testid="vuln-cvssv3-pr">\s*(.*?)\s*<\/span>'
                PrivilegesRequired = str(
                    re.findall(string, soup)[0])  # None
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            UserInteraction = None
            try:
                string = '<strong>User Interaction \(UI\):\s*<\/strong>\s*<span data-testid="vuln-cvssv3-ui">\s*(.*?)\s*<\/span>'
                UserInteraction = str(
                    re.findall(string, soup)[0])  # None
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            Scope = None
            try:
                string = '<strong>Scope \(S\):\s*<\/strong>\s*<span data-testid="vuln-cvssv3-s">\s*(.*?)\s*<\/span>'
                Scope = str(re.findall(string, soup)[0])  # Changed
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            CVSSV3Confidentiality = None
            try:
                string = '<strong>Confidentiality \(C\):\s*<\/strong>\s*<span data-testid="vuln-cvssv3-c">\s*(.*?)\s*<\/span>'
                CVSSV3Confidentiality = str(
                    re.findall(string, soup)[0])  # Partial
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            CVSSV3Integrity = None
            try:
                string = '<strong>Integrity \(I\):\s*<\/strong>\s*<span data-testid="vuln-cvssv3-i">\s*(.*?)\s*<\/span>'
                CVSSV3Integrity = str(
                    re.findall(string, soup)[0])  # None
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            CVSSV3Availability = None
            try:
                string = '<strong>Availability \(A\):\s*<\/strong>\s*<span data-testid="vuln-cvssv3-a">\s*(.*?)\s*<\/span>'
                CVSSV3Availability = str(
                    re.findall(string, soup)[0])  # High
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            CVSSv2BaseScore = None
            try:
                string = '<span data-testid="vuln-cvssv2-base-score">(.*?) <\/span>'
                CVSSv2BaseScore = float(
                    re.findall(string, soup)[0])  # 7.5
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            ImpactSubscore = None
            try:
                string = '<strong>Impact Subscore:<\/strong>\s*<span data-testid="vuln-cvssv2-impact-subscore">\s*(.*?)\s*<\/span>'
                ImpactSubscore = float(
                    re.findall(string, soup)[0])  # 2.9
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            ExploitabilitySubscore = None
            try:
                string = '<strong>Exploitability Subscore:<\/strong>\s*<span data-testid="vuln-cvssv2-exploitability-score">\s*(.*?)\s*<\/span>'
                ExploitabilitySubscore = float(
                    re.findall(string, soup)[0])  # 10.0
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            AccessVector = None
            try:
                string = '<strong>Access Vector \(AV\):\s*<\/strong>\s*<span data-testid="vuln-cvssv2-av">\s*(.*?)\s*<\/span>'
                AccessVector = str(re.findall(
                    string, soup)[0])  # Network
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            AccessComplexity = None
            try:
                string = '<strong>Access Complexity \(AC\):\s*<\/strong>\s*<span data-testid="vuln-cvssv2-ac">\s*(.*?)\s*<\/span>'
                AccessComplexity = str(
                    re.findall(string, soup)[0])  # Low
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            Authentication = None
            try:
                string = '<strong>Authentication \(AU\):\s*<\/strong>\s*<span data-testid="vuln-cvssv2-au">\s*(.*?)\s*<\/span>'
                Authentication = str(
                    re.findall(string, soup)[0])  # None
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            CVSSV2Confidentiality = None
            try:
                string = '<strong>Confidentiality \(C\):\s*<\/strong>\s*<span data-testid="vuln-cvssv\d-c">\s*(.*?)\s*<\/span>\s*<br \/>\s*<strong>Integrity \(I\):\s*<\/strong>\s*<span data-testid="vuln-cvssv2-i">'
                CVSSV2Confidentiality = str(
                    re.findall(string, soup)[0])  # Partial
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            CVSSV2Integrity = None
            try:
                string = '<strong>Integrity \(I\):\s*<\/strong>\s*<span data-testid="vuln-cvssv2-i">\s*(.*?)\s*<\/span>'
                CVSSV2Integrity = str(
                    re.findall(string, soup)[0])  # None
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            CVSSV2Availability = None
            try:
                string = '<strong>Availability \(A\):\s*<\/strong>\s*<span data-testid="vuln-cvssv2-a">\s*(.*?)\s*<\/span>'
                CVSSV2Availability = str(re.findall(string, soup)[0])  # High
            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            Additional_Information = None
            try:
                string = '<span data-testid="vuln-cvssv2-additional">\s*(.*?<br \/>)\s*<\/span>'
                # Allows unauthorized disclosure of information , Allows unauthorized modification , Allows disruption of service
                Additional_Information = str(
                    re.findall(string, soup)[0])
                # print(Additional_Information)
                string = '(.*?)<br \/>'
                Additional_Information = re.findall(string, Additional_Information)
                # print(Additional_Information)

            except Exception as e:
                pass
                # print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))

            configurations=0
            try:
                string='<strong data-testid="vuln-software-config.*?">Configuration(.*?)<\/strong>'
                configurations = len(re.findall(string,soup))
            except:
                configurations=0

            featureJson = {
                'CVE_ID': match[i][1],
                'url': url,
                'publish_date': OriginalReleaseDate,
                'update_date': LasTrevised,
                'overview': Overview,
                'CWE': CWE,
                'CVSS_v3_Base_Score': CVSSv3BaseScore,
                'CVSS_v3_Impact_Score': ImpactScore,
                'CVSS_v3_Exploitability_Score': ExploitabilityScore,
                'CVSS_v3_Attack_Vector': AttackVector,
                'CVSS_v3_Attack_Complexity': AttackComplexity,
                'CVSS_v3_Privileges_Required': PrivilegesRequired,
                'CVSS_v3_User_Interaction': UserInteraction,
                'CVSS_v3_Scope': Scope,
                'CVSS_v3_Confidentiality': CVSSV3Confidentiality,
                'CVSS_v3_Integrity': CVSSV3Integrity,
                'CVSS_v3_Availability': CVSSV3Availability,
                'CVSS_v2_Base_Score': CVSSv2BaseScore,
                'CVSS_v2_Impact_Subscore': ImpactSubscore,
                'CVSS_v2_Exploitability_Subscore': ExploitabilitySubscore,
                'CVSS_v2_Access_Vector': AccessVector,
                'CVSS_v2_Access_Complexity': AccessComplexity,
                'CVSS_v2_Authentication': Authentication,
                'CVSS_v2_Confidentiality': CVSSV2Confidentiality,
                'CVSS_v2_Integrity': CVSSV2Integrity,
                'CVSS_v2_Availability': CVSSV2Availability,
                'CVSS_v2_Impact_Type': Additional_Information,
                'References': References_all,
                'date_entry_created': DateEntryCreated,
                'configurations': configurations,
                'patch_date':PatchDate
            }
            # print(featureJson)
            print(json.dumps(featureJson, indent=2))
        except Exception as e:
            print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))
            print('skip cve', str(match[i][1]))
        try:
            '''如果有在es裡，更新資料'''
            if len(response["hits"]["hits"]) > 0:
                print('already in es ,updating...', str(match[i][1]))
                ES_ip.index(index=esname, doc_type='nvd',body=featureJson, id=response["hits"]["hits"][0]["_id"])

            # print response
            else:
                '''如果沒有在es裡，新增資料'''
                print("add: ", str(match[i][1]))
                ES_ip.index(index=esname,doc_type='nvd', body=featureJson)
        except Exception as e:
            print('--Error on line {}'.format(sys.exc_info()[-1].tb_lineno) + str(e))
            print('skip cve', str(match[i][1]))

'''進入每一個月，抓每一頁的CVE資料'''
def getMonth(y, m,esname):
    print(y, m,esname)
    res = requests.get( "https://nvd.nist.gov/full_listing.cfm?year=" + str(y) + "&month=" + str(m))

    # convert to SOUP
    soup = str(BeautifulSoup(res.text,"lxml"))
    #     print soup

    string = '<span class="col-md-2"> <a href="(.*?)">(.*?)<\/a><\/span>'
    match = re.findall(string, soup)
    # print((match))
    insert(match,esname)

def getNVD():
    '''log紀錄執行狀況'''
    logsFunction.appendWrite('NVD')

    '''抓現在的時間'''
    global t 
    t= datetime.now()
    print('The time is : ', t)

    global year
    year=int(t.year)
    month=int(t.month)
    
    #現在是1月的時候 爬到去年12月
    if (month == 1):
        esname = "sec_nvd-"+str(year)
        # 建立es 的index，依據年份  
        try:
            res = ES_ip.indices.create(index=esname)
        except Exception as e:
            pass

        logsFunction.appendWrite('開始抓'+str(year)+'/'+ str(month)+'月的資料')
        print('開始抓'+str(year)+'/'+ str(month)+'月的資料')
        getMonth(year, month,esname)
        logsFunction.appendWrite('開始抓'+str(year-1)+'/'+ str(12)+'月的資料')
        print('開始抓'+str(year-1)+'/'+ str(12)+'月的資料')

        getMonth((year-1), (12),esname)
    #抓當月以及上一個月的
    else:
        esname = "sec_nvd-"+str(year)
        # 建立es 的index，依據年份  
        try:
            res = ES_ip.indices.create(index=esname)
        except Exception as e:
            # print("Index already exists")
            pass

        logsFunction.appendWrite('開始抓'+str(year)+'/'+ str(month)+'月的資料')
        print('開始抓'+str(year)+'/'+ str(month)+'月的資料')
        getMonth(year, month,esname)
        logsFunction.appendWrite('開始抓'+str(year)+'/'+ str(month-1)+'月的資料')
        print('開始抓'+str(year)+'/'+ str(month-1)+'月的資料')
        getMonth((year), (month-1),esname)
        
@click.command()
@click.option('--es_ip', type=str,default='211.23.163.51')
@click.option('--es_port', type=str, default='59200')
#60分鐘執行一次
def run(es_ip,es_port):
    global ES_ip
    ES_ip = Elasticsearch(es_ip+":"+es_port)
    '''log紀錄執行狀況'''
    global logsFunction
    logsFunction = LogsFunc("NVD")
    getNVD()
    
if __name__ == '__main__':
    run()