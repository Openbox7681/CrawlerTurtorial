# 輿情爬蟲程式說明
## 開發環境與使用套件說明
* python - 2.7.12 (https://www.python.org/)
* Beautiful Soup - 4.4.0 (https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
* Requests - 2.19.1(http://docs.python-requests.org/en/master/)
* Elasticsearch - 6.3.1 (https://elasticsearch-py.readthedocs.io/en/6.3.1/api.html)
* UserAgent - 0.1.10 (https://pypi.org/project/fake-useragent/)
* mysql-connector - 2.0.4(https://dev.mysql.com/downloads/connector/python/8.0.html)

## ES 與 Mysql設定檔
    crawler/lib/crawler_config.ini
* ES版本 - 6.3.2
* Mysql版本 - 5.7
## 爬蟲專案目錄
### 預計撰寫之網站
* [聯合新聞網](https://udn.com/news/index) done!

    執行路徑 : crawler/project/udn/udn.py 
* [自由時報](http://www.ltn.com.tw/) No!

    執行路徑: crawler/project/itn/itn.py 
* [蘋果日報](https://tw.appledaily.com/)done!

    執行路徑 : crawler/project/appleDaily/appleDaily.py
* [中時電子報](http://www.chinatimes.com/)

    執行路徑 : crawler/project/chinatimes/chinatimes.py 還未執行
* [iThome](https://www.ithome.com.tw/news) done!

    執行路徑: crawler/project/ithome/ithome.py
* [奇摩新聞](https://tw.news.yahoo.com/)done!

    執行路徑 : crawler/project/yahoo/yahoo.py
* [技服中心資安新聞](http://www.nccst.nat.gov.tw/NewsRSS?RSSType=news&lang=zh)
* [數位時代](https://www.bnext.com.tw/) done!

    執行路徑 : crawler/project/bnext/bnext.py
* [資安人](https://www.informationsecurity.com.tw/main/index.aspx)done!

    執行路徑 : crawler/project/informationsecurity/informationsecurity.py
* [科技新報-資訊安全](http://technews.tw/category/internet/%E8%B3%87%E8%A8%8A%E5%AE%89%E5%85%A8/)

    執行路徑 : crawler/project/technews/technews.py 還未執行
* [新頭殼](https://newtalk.tw/)done!

    執行路徑 : crawler/project/newtalk/newtalk.py
* [ETtooday新聞雲](https://www.ettoday.net/)
* [趨勢-資安趨勢部落格](https://blog.trendmicro.com.tw/)done!

    執行路徑 : crawler/project/trendmicro/trendmicro.py
* [今日新聞](https://www.nownews.com/)
