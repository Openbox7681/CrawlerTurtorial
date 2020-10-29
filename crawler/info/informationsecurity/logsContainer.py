#!/usr/bin/python
# -*- coding: UTF-8 -*-


import datetime
import os

class LogsFunc():

    def __init__(self, folderName):
        """
        parent_path = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + "/../../logs")
        folderName = parent_path+"/"+folderName
        now_day = datetime.datetime.now().strftime("%Y-%m")
        # print now_day
        # self._folderPath = folderName + "/" + now_day
        if not os.path.isdir(folderName):
            os.mkdir(folderName)
            self._folderPath = folderName + "/" + now_day
            if not os.path.isdir(self._folderPath):
                os.mkdir(self._folderPath)
        else:
            self._folderPath = folderName + "/" + now_day
            if not os.path.isdir(self._folderPath):
                os.mkdir(self._folderPath)
        now_time = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
        self._path =  self._folderPath + '/' +now_time  +".txt"
        """
        pass

    def appendWrite(self, data):
        """
        file = open(self._path, "a")
        data = datetime.datetime.now().strftime("%Y-%m-%d %H%M%S") +"\t,\t"+ data
        file.write(data)
        file.write('\n')
        file.close()
        """
        pass
