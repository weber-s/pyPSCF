# -*-coding:Utf-8 -*
import datetime
import calendar
import os
import sys
import re
import json
import shutil


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

    # ===== Write the SETUP.CFG file                    =======================
    shutil.copy(os.path.normpath('parameters/SETUP_backTraj.CFG'), dirHysplit+"SETUP.CFG")
    # go to the hysplit dir
    os.chdir(dirHysplit)
    # ===== Compute the Back Traj                       =======================
    while datetime.datetime(YYend+2000, MMend, DDend, HHend) >= datetime.datetime(int(YY)+2000, int(MM), int(DD), int(HH)):
        if not os.path.exists(dirOutput+"traj_"+param["station"]+"_"+YY+MM+DD+HH):
            ## create file name
            #file1, previous month
            if MM=="01":
                mon="dec"
                year=str(int(YY)-1)
            else:
                mon=datetime.datetime(int(YY)+2000, int(MM)-1, 1).strftime("%b").lower()
                year=YY
            file1="gdas1."+mon+year+".w5"
            if not os.path.exists(dirGDAS+file1):
                file1="gdas1."+mon+year+".w4"
            #other file (all the current month)
            mon=datetime.datetime(int(YY)+2000, int(MM), 1).strftime("%b").lower()
            year=YY
            file2="gdas1."+mon+year+".w1"
            file3="gdas1."+mon+year+".w2"
            file4="gdas1."+mon+year+".w3"
            file5="gdas1."+mon+year+".w4"
            file6="gdas1."+mon+year+".w5"
            if not os.path.exists(dirGDAS+file6):
                file6=''
    
            #Write the CONTROL file
            f = open(CONTROL, 'w')
            f.write("%s %s %s %s\n" % (YY, MM, DD, HH))
            f.write("1\n")
            f.write("%s %s %s\n" % (param["lat"], param["lon"], param["alt"]))
            f.write("%s\n" % param["hBT"])
            f.write("0\n")
            f.write("10000.0\n")
            if file6 != '':
                f.write("6\n")
            else:
                f.write("5\n")
            f.write("%s\n" % dirGDAS)
            f.write("%s\n" % file1)
            f.write("%s\n" % dirGDAS)
            f.write("%s\n" % file2)
            f.write("%s\n" % dirGDAS)
            f.write("%s\n" % file3)
            f.write("%s\n" % dirGDAS)
            f.write("%s\n" % file4)
            f.write("%s\n" % dirGDAS)
            f.write("%s\n" % file5)
            if file6 != '':
                f.write("%s\n" % dirGDAS)
                f.write("%s\n" % file6)
            f.write("%s\n" % dirOutput)
            f.write("traj_%s_%s%s%s%s" % (param["station"], YY, MM, DD, HH))
            f.close()
            os.system(HysplitExec)
    
        HH=int(HH)+int(param["stepHH"])
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
    
    # Convert the file for the PSCF
    #filelist = os.listdir(dirOutput)
    #for file in filelist:
    #    nameout=dirConverted+file+'_converted.txt'
    #    fileout=open(nameout,'w')
    #    f=open(dirOutput+file)
    #    lines=f.readlines()
    #    l=int(lines[0].replace(' ','')[0])
    #    for i in range(l+4,len(lines)):
    #        regex=re.compile(r'[\r\n\t]')
    #        line=regex.sub(" ",lines[i])
    #        line=re.split(' *', line)
    #        line=line[2:len(line)-1]
    #        #line = filter(None, lines[i].strip().split(' '))
    #        lineout=''
    #        lineout='%3.3f' % (float(line[2]),)
    #        for j in range(3,len(line)):
    #            lineout+=';%3.3f' % (float(line[j]),)
    #        #lineout+=';%f \n' % (float(line[len(line)-1]),)
    #        lineout+=' \n'
    #        fileout.write(lineout)
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
