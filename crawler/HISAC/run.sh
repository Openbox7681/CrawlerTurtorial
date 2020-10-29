#!/bin/sh

if [ "x$ES_IP" = "x" ]; then 
  ES_IP="211.23.163.51"
fi

if [ "x$ES_PORT" = "x" ]; then 
  ES_PORT="59200"
fi

python3 main.py --es_ip $ES_IP:$ES_PORT
