#!/usr/bin/python
# -*- coding: UTF-8 -*-


import datetime
import os

class LogsFunc():

    def __init__(self, folderName):
        now_day = datetime.datetime.now().strftime("%Y-%m-%d")
        # print(now_day)
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

    def appendWrite(self, data):
        now_time = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
        # assert isinstance(fileName, object)
        _path = self._folderPath + '/' +now_time  +".txt"
        file = open(_path, "a")
        data = datetime.datetime.now().strftime("%Y-%m-%d %H%M%S") +"\t,\t"+ data
        file.write(data)
        file.write('\n')
        file.close()


'''
if __name__ == '__main__':
    print('____start read file___')
    print "取得當下目錄："+os.getcwd()
    now = datetime.datetime.now()
    now_day = datetime.datetime.now().strftime("%Y-%m-%d")
    print '____now_day___',now_day
    func = FuncFile(now_day)
    func.checkFolder()
    # now_time = datetime.datetime.now().strftime("%H%M%S")
    now_time = datetime.datetime.now().strftime("%H%M")
    now_time = now_day+"_"+now_time
    func = FuncFile(now_day)
    print '____now_time___',now_time
    func.appendWrite(now_time,"a")
    func.appendWrite(now_time,"b")
    func.appendWrite(now_time,"c")
'''