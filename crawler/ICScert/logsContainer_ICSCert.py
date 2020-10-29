#!/usr/bin/python
# -*- coding: UTF-8 -*-


import datetime
import os

class LogsFunc():

    def __init__(self, folderName):
        now_day = datetime.datetime.now().strftime("%Y-%m-%d")
        # print now_day
        # self._folderPath = folderName + "/" + now_day
        if not os.path.isdir(folderName):
            os.mkdir(folderName)
            self._folderPath_log = folderName + "/" + now_day
            if not os.path.isdir(self._folderPath_log):
                os.mkdir(self._folderPath_log)

            self._folderPath_id = folderName + "/data"
            if not os.path.isdir(self._folderPath_id):
                os.mkdir(self._folderPath_id)
        else:
            self._folderPath_log = folderName + "/" + now_day
            if not os.path.isdir(self._folderPath_log):
                os.mkdir(self._folderPath_log)
                
            self._folderPath_id = folderName + "/data"
            if not os.path.isdir(self._folderPath_id):
                os.mkdir(self._folderPath_id)


    def appendWriteError(self, data):
        now_time = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
        # assert isinstance(fileName, object)
        _path = self._folderPath_log + '/' +now_time  +".txt"
        # print(_path)
        file = open(_path, "a")
        data = datetime.datetime.now().strftime("%Y-%m-%d %H%M%S") +"\t"+ data
        file.write(data)
        file.write('\n')
        file.close()

    def appendWrite(self, data,id):
        # now_time = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
        # assert isinstance(fileName, object)
        _path = self._folderPath_id + '/' + id +".txt"
        # print(_path)
        file = open(_path, "a")
        data = datetime.datetime.now().strftime("%Y-%m-%d %H%M%S") +"\t"+ data
        file.write(data)
        file.write('\n')
        file.close()