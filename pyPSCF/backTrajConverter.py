# -*-coding:Utf-8 -*
import re
import os

def BTconverter():
    #Convert the file for the PSCF
    with open('localParamBackTraj.json', 'r') as dataFile:
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
