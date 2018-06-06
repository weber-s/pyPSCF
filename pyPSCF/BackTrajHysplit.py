import os
import sys
import numpy as np
import time
import datetime as dt
import calendar
import re
import json
import shutil


def file_exists(path):
    return os.path.exists(path)

def update_date(YY, MM, DD, HH, stepHH):
    HH=int(HH)+int(stepHH)
    if HH>=24:
        HH="00"
        DD=int(DD)+1
        if DD == int(calendar.monthrange(int(YY)+2000, int(MM))[1]+1):
            DD="01"
            MM=int(MM)+1
            if MM==13:
                MM="01"
                YY=int(YY)+1
    HH=str(HH)
    DD=str(DD)
    MM=str(MM)
    YY=str(YY)
    if len(HH)==1:
        HH="0"+HH
    if len(DD)==1:
        DD="0"+DD
    if len(MM)==1:
        MM="0"+MM

    return (YY, MM, DD, HH)

def BT():
    """
    Compute the back-trajectory according to the parameters in parameters/localParamBackTraj.json.
    
    It should be use eithery with GUI.pyw otherwise or from the '../parameters'
    dir, ortherwise the relative path won't be effective.
    """

    # ===== Load the parameters from the json file          ===================
    with open(os.path.normpath('parameters/localParamBackTraj.json'), 'r') as dataFile:
        param=json.load(dataFile)
    YY,MM,DD,HH = int(param["date"][0]),int(param["date"][1]),int(param["date"][2]),int(param["date"][3])
    YYend,MMend,DDend,HHend = int(param["dateEnd"][0]), int(param["dateEnd"][1]), int(param["dateEnd"][2]), int(param["dateEnd"][3])
    
    dirOutput       = param["dirOutput"]+os.sep
    HysplitExec     = param["dirHysplit"]+os.sep+"exec"+os.sep+"hyts_std"
    if sys.platform=="win32":
        HysplitExec += ".exe"
    dirHysplit      = param["dirHysplit"]+os.sep+"working"+os.sep
    dirGDAS         = param["dirGDAS"]+os.sep
    CONTROL         = dirHysplit+"CONTROL"
    
#    if not os.path.exists(dirGDAS):
#        print("The path for the GDAS file is wrong...")
#        return 0
#    if not os.path.exists(dirHysplit) or not os.path.exists(HysplitExec):
#        print("The Hysplit directory or the 'hyts_std' command do not exist...")
#        return 0
#    if os.path.exists(dirOutput)==False:
#        if sys.version_info.major >= 3:
#            a=str(input("The output directory does not exist. Make one? ([y],n) "))
#        else:
#            a=str(raw_input("The output directory does not exist. Make one? ([y],n) "))
#        if a=="y" or a=="Y" or a=="\n" or a=="yes":
#            os.makedirs(dirOutput)
#        else:
#            print("Script exit")
#            return 0
#    if not os.path.exists(dirConverted):
#        if sys.version_info.major >= 3:
#            a=str(input("The output converted directory does not exist. Make one? ([y],n) "))
#        else:
#            a=str(raw_input("The output converted directory does not exist. Make one? ([y],n) "))
#        if a=="y" or a=="Y" or a=="\n" or a=="yes":
#            os.mkdir(dirConverted)
#        else:
#            print("Script exit")
#            return 0

    YY, MM, DD, HH = update_date(YY, MM, DD, HH, param["stepHH"])

    # ===== Write the SETUP.CFG file                    =======================
    shutil.copy(os.path.normpath('parameters/SETUP_backTraj.CFG'), dirHysplit+"SETUP.CFG")
    # go to the hysplit dir
    os.chdir(dirHysplit)
    # ===== Compute the Back Traj                       =======================
    while dt.datetime(YYend+2000, MMend, DDend, HHend) >= dt.datetime(int(YY)+2000, int(MM), int(DD), int(HH)):
        currentFile = "traj_"+param["station"]+"_"+YY+MM+DD+HH
        if file_exists(dirOutput+currentFile):
            YY, MM, DD, HH = update_date(YY, MM, DD, HH, param["stepHH"])
            print("file already exist :", currentFile)
            continue
        cfile = open(CONTROL, "r").readlines()
        if currentFile in cfile[-1].strip():
            YY, MM, DD, HH = update_date(YY, MM, DD, HH, param["stepHH"])
            print("file is already processing:", currentFile)
            time.sleep(np.random.rand()*3)
            continue
        #if not file_exists(dirOutput+currentFile):
        ## create file name
        #file1, previous month
        if MM=="01":
            mon = "dec"
            year = str(int(YY)-1)
        else:
            mon = dt.datetime(int(YY)+2000, int(MM)-1, 1).strftime("%b").lower()
            year = YY
        file1 = "gdas1."+mon+year+".w5"
        if not os.path.exists(dirGDAS+file1):
            file1 = "gdas1."+mon+year+".w4"
        #other file (all the current month)
        mon = dt.datetime(int(YY)+2000, int(MM), 1).strftime("%b").lower()
        year = YY
        file2 = "gdas1."+mon+year+".w1"
        file3 = "gdas1."+mon+year+".w2"
        file4 = "gdas1."+mon+year+".w3"
        file5 = "gdas1."+mon+year+".w4"
        file6 = "gdas1."+mon+year+".w5"
        if not os.path.exists(dirGDAS+file6):
            file6 = ''

        #Write the CONTROL file
        f =  "%s %s %s %s\n" % (YY, MM, DD, HH)
        f += "1\n"
        f += "%s %s %s\n" % (param["lat"], param["lon"], param["alt"])
        f += "%s\n" % param["hBT"]
        f += "0\n"
        f += "10000.0\n"
        if file6 != '':
            f += "6\n"
        else:
            f += "5\n"
        f += "%s\n" % dirGDAS
        f += "%s\n" % file1
        f += "%s\n" % dirGDAS
        f += "%s\n" % file2
        f += "%s\n" % dirGDAS
        f += "%s\n" % file3
        f += "%s\n" % dirGDAS
        f += "%s\n" % file4
        f += "%s\n" % dirGDAS
        f += "%s\n" % file5
        if file6 != '':
            f += "%s\n" % dirGDAS
            f += "%s\n" % file6
        f += "%s\n" % dirOutput
        f += "traj_%s_%s%s%s%s\n" % (param["station"], YY, MM, DD, HH)
        if not file_exists(dirOutput+currentFile):
            file = open(CONTROL, 'w')
            file.write(f)
            file.close()
            print("Processing : ", currentFile)
            os.system(HysplitExec)
            time.sleep(np.random.rand()*3)
    
        YY, MM, DD, HH = update_date(YY, MM, DD, HH, param["stepHH"])

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


