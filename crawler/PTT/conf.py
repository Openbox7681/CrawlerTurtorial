import json, psutil
from elasticsearch import Elasticsearch
from datetime import datetime
#setting ES
class ES_init_k8s:
	#k8s測試機
    ip_port = "192.168.70.182:30200"
	#local 測試
	# ip_port = "127.0.0.1:9200"

class ES_init:
	ip_port = "211.23.163.51:19200"

#setting mysql
class mysql_init:
	ip = "192.168.163.52"
	port = 8459
	user = "dbuser"
	password = "icst4iii"
#seeting flask
class flask_init:
	ip = "127.0.0.1"

def error_define(status,message):
	try:
		js = {"status":status,"message":json.loads(message)}
	except:
		js = {"status":status,"message":message}
	js = json.dumps(js, indent = 2,default = datetime_handler)
	return js

def kill_process(parent):
	for child in parent.children(recursive=True):
		child.kill()
	parent.kill()

def datetime_handler(x):
	if isinstance(x, datetime.datetime):
		return x.isoformat()
	raise TypeError("Unknown type")


es = Elasticsearch(ES_init_k8s.ip_port)
