import mysql.connector
import ConfigParser
import os


class ConnectMYsql():
    def __init__(self, _username, _password, _host, _port, _database):
        #cf = ConfigParser.ConfigParser()
        #cf.read("crawler/lib/crawler_config.ini")
        self.Mysql_username=_username
        self.Mysql_password=_password
        self.Mysql_host=_host
        self.Mysql_port=_port
        self.Mysql_database=_database
        self.conn = mysql.connector.connect(
            user=self.Mysql_username,
            password=self.Mysql_password,
            host=self.Mysql_host,
            port=self.Mysql_port,
            database=self.Mysql_database) 
    def update(self, _crawlername, _isimmediate, _status, _pid, _lastupdatetime, _total):
        cur = self.conn.cursor()
        query = "UPDATE crawler SET IsImmediate=%s, Status=%s, Pid=%s, LastUPdateTime=%s, Datacount=%s WHERE crawler.Crawlerkey=%s"
        cur.execute(query, (_isimmediate, _status, _pid, _lastupdatetime,_total, _crawlername))
        self.conn.commit()
        query = "SELECT IsImmediate, Status, Pid, LastUpdateTime, Datacount FROM ttc_secbuzzer.crawler WHERE Crawlerkey=" + "'" + _crawlername + "'"
        cur.execute(query)
        for item in cur:
            print item
        cur.close()

