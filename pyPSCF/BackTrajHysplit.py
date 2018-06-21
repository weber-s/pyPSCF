import os
import sys
import numpy as np
import time
import datetime as dt
from dateutil.relativedelta import relativedelta
import calendar
import re
import json
import shutil
import pandas as pd


def file_exists(path):
    return os.path.exists(path)

def get_currentFile(station, d):
    formatDate = dt.datetime.strftime(d, "%y%m%d%H")
    return "traj_"+station+"_"+formatDate

def update_date(d, stepHH):
    return d + pd.Timedelta(stepHH+"H")

def BT():
    """
    Compute the back-trajectory according to the parameters in parameters/localParamBackTraj.json.
    
    It should be use eithery with GUI.pyw otherwise or from the '../parameters'
    dir, ortherwise the relative path won't be effective.
    """

    # ===== Load the parameters from the json file          ===================
    with open(os.path.normpath('parameters/localParamBackTraj.json'), 'r') as dataFile:
        param=json.load(dataFile)

    curDate = pd.to_datetime(param["dateMin"])
    endDate = pd.to_datetime(param["dateMax"])
    # YY,MM,DD,HH = int(param["date"][0]),int(param["date"][1]),int(param["date"][2]),int(param["date"][3])
    # YYend,MMend,DDend,HHend = int(param["dateEnd"][0]), int(param["dateEnd"][1]), int(param["dateEnd"][2]), int(param["dateEnd"][3])
    
    dirOutput       = param["dirOutput"]+os.sep
    HysplitExec     = param["dirHysplit"]+os.sep+"exec"+os.sep+"hyts_std"
    if sys.platform=="win32":
        HysplitExec += ".exe"
    dirHysplit      = param["dirHysplit"]+os.sep+"working"+os.sep
    dirGDAS         = param["dirGDAS"]+os.sep
    CONTROL         = dirHysplit+"CONTROL"
    

    curDate = update_date(curDate, param["stepHH"])

    # ===== Write the SETUP.CFG file                    =======================
    shutil.copy(os.path.normpath('parameters/SETUP_backTraj.CFG'), dirHysplit+"SETUP.CFG")
    # go to the hysplit dir
    os.chdir(dirHysplit)
    # ===== Compute the Back Traj                       =======================
    while endDate >= curDate: #dt.datetime(YYend+2000, MMend, DDend, HHend) >= dt.datetime(int(YY)+2000, int(MM), int(DD), int(HH)):
        currentFile = get_currentFile(param["station"], curDate)
        if file_exists(dirOutput+currentFile):
            curDate = update_date(curDate, param["stepHH"])
            print("file already exist :", currentFile)
            continue
        cfile = open(CONTROL, "r").readlines()
        if currentFile in cfile[-1].strip():
            curDate = update_date(curDate, param["stepHH"])
            print("file is already processing:", currentFile)
            time.sleep(np.random.rand()*3)
            continue
        #if not file_exists(dirOutput+currentFile):
        ## create file name
        #file1, previous month
        preDate = curDate + relativedelta(months=-1)
        mon = dt.datetime.strftime(preDate, "%b").lower()
        year = dt.datetime.strftime(preDate, "%y")
        files = []
        
        files = ["gdas1."+mon+year+".w{i}".format(i=i) for i in range(1,6)]
        #other file (all the current month)
        mon = dt.datetime.strftime(curDate, "%b").lower()
        year = dt.datetime.strftime(curDate, "%y")
        files += ["gdas1."+mon+year+".w{i}".format(i=i) for i in range(1,6)]
        #file7, next month
        nextDate = curDate + relativedelta(months=1)
        mon = dt.datetime.strftime(nextDate, "%b").lower()
        year = dt.datetime.strftime(nextDate, "%y")
        files += ["gdas1."+mon+year+".w1"]
        for f in files:
            if not os.path.exists(dirGDAS+f):
                files.remove(f)

        #Write the CONTROL file
        YY = dt.datetime.strftime(curDate, "%y")
        MM = dt.datetime.strftime(curDate, "%m")
        DD = dt.datetime.strftime(curDate, "%d")
        HH = dt.datetime.strftime(curDate, "%H")
        f =  "%s %s %s %s\n" % (YY, MM, DD, HH)
        f += "1\n"
        f += "%s %s %s\n" % (param["lat"], param["lon"], param["alt"])
        f += "%s\n" % param["hBT"]
        f += "0\n"
        f += "10000.0\n"
        f += "%s\n" % len(files)
        for file in files:
            f += "%s\n" % dirGDAS
            f += "%s\n" % file
        f += "%s\n" % dirOutput
        f += "%s\n" % currentFile
        if not file_exists(dirOutput+currentFile):
            file = open(CONTROL, 'w')
            file.write(f)
            file.close()
            print("Processing : ", currentFile)
            os.system(HysplitExec)
            time.sleep(np.random.rand()*3)
    
        curDate = update_date(curDate, param["stepHH"])

    return 1


def BTconverter():
    """
    Depreciated.
    Was used when the PSCF4GUI.py script didn't worked with hysplit format. Now
    it's ok.
    """
    #Convert the file for the PSCF
    with open(os.normpath('parameters/localParamBackTraj.json'), 'r') as dataFile:
        param=json.load(dataFile)
    dirOutput       = param["dirOutput"]+os.sep+param["station"]+os.sep+"raw"+os.sep
    dirConverted    = param["dirOutput"]+os.sep+param["station"]+os.sep+"converted"+os.sep
    
    
    filelist = os.listdir(dirOutput)
    for file in filelist:
        f=open(dirOutput+file)
        lines=f.readlines()
        f.close()
    
        ##find where the BT data starts (number of meteo file + 4)
        l=int(lines[0].replace(' ','')[0])
        
        ##find where the rainfall lives
        #lineRainfall= lines[l+3]
        #idxRainfall = 12 + lineRainfall.split().index('RAINFALL')
    
        nameout=dirConverted+file+'_converted.txt'
        fileout=open(nameout,'w')
    
        regex=re.compile(" +")
        for i in range(l+4,len(lines)):
            lineout=re.sub(regex, ";",lines[i].strip())
            lineout+='\n'
            fileout.write(lineout)
        fileout.close()


