# -*-coding:Utf-8 -*
import sys, os
import datetime as dt
import numpy as np
import json
import scipy
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
from scipy import signal
import scipy.stats as sst
import math
from multiprocessing import Process
import linecache
import pandas as pd

# tkinter modules
if sys.version_info.major >= 3:
    from tkinter.messagebox import *
    #sys.exit("You have to run it with python 2, not python 3.")
else:
    # we are on Python 2
    from tkMessageBox import *


def extractBackTraj(date, conc, add_hour, folder, prefix, run=72, rainBool=True):
    """
    Sum up back trajectories file into a pandas DataFrame.

    Parameters
    ----------
    date :
    conc : 
    add_hour :
    folder :
    prefix :
    run :
    rainBool:

    Return
    ------
    df : pd.DataFrame
    """
    df = pd.DataFrame()
    for d in range(len(date)):
        # find all back traj for the date d
        for hour in add_hour:
            # open back traj file
            name = prefix + aammddhh(date[d]+dt.timedelta(hours=hour))
            datafile=os.path.join(folder, name)
            if not os.path.isfile(datafile):
                print('Back-trajectory {} file is missing'.format(name))
                continue
            else:
                # add the lon/lat of the BT
                nb_line_to_skip = linecache.getline(datafile, 1).split()
                nb_line_to_skip = int(nb_line_to_skip[0])
                meteo_idx = linecache.getline(datafile, nb_line_to_skip+4).split()
                idx_names = ["a","b","year","month","day","hour","c","d","run","lat","lon","alt"]
                idx_names = np.hstack((idx_names,meteo_idx[1:]))

                traj = pd.read_table(datafile,
                                     delim_whitespace=True,
                                     header=None,
                                     names=idx_names,
                                     skiprows=nb_line_to_skip+4,
                                     nrows=run)
                lat = traj["lat"]
                lon = traj["lon"]
                rain = traj["RAINFALL"]

                # if it was raining at least one time, we cut it
                if rainBool and any(rain>0):
                    idx_rain = np.where(rain!=0)[0][0]
                    lat = lat[:idx_rain]
                    lon = lon[:idx_rain]

                dftmp = pd.DataFrame(data={"date":date[d],
                                           "dateBT":date[d]+dt.timedelta(hours=hour),
                                           "conc":conc[d],
                                           "lon":lon,
                                           "lat":lat})
                
                df = pd.concat([df,dftmp])

    return df

def str2date(strdate):
    # "31/10/2010 22:34"
    date=list()
    print(strdate)
    for d in strdate:
        if d=='':
            return float(-999)
        date.append(dt.datetime.strptime(d, '%d/%m/%Y %H:%M'))
    date = np.array(date)
    return(date)

def specie2study(Cfile, sp):
    header=np.genfromtxt(Cfile, delimiter=';', max_rows=1, dtype=str)
    j=-999
    for i in range(0, header.size):
        if header[i].upper()==sp.upper():
            j=i
    return(j)

def dateformat(a):
    if len(a)==1:
        return '0%s' % (a,)
    else:
        return a

def aammddhh(x):
    yy=str(x.year)[2:]
    mm=dateformat(str(x.month))
    dd=dateformat(str(x.day))
    hh=dateformat(str(x.hour))
    return '%s%s%s%s' % (yy,mm,dd,hh)    ##needs to be adapted

def unique2d(a):
    x, y = a
    b = x + y*1.0j
    idx = np.unique(b,return_index=True)[1]
    return a[:,idx]

def arr2json(arr):
    return json.dumps(arr.tolist())

def json2arr(astr,dtype):
    return np.fromiter(json.loads(astr),dtype)

def toRad(x):
    return x*math.pi/180

def toDeg(x):
    return x*180/math.pi

# =============================================================================
# =============================================================================
# =============================================================================
# =============================================================================
class PSCF:
    """
    The main PSCF function. Compute the PSCF according to the parameters in 'localParamPSCF.json'.
    The argument is the rank of the specie in the "species" in the 'localParamPSCF.json' file.
    If no argument is given, assume that there is only one specie and takes the first one.
    """
    def __init__(self, station, specie, lat0, lon0, folder, prefix, add_hour, resQuality,
                 percentile, threshold, concFile, dateMin, dateMax, wfunc=True,
                 wfunc_type="auto", smoothplot=True, mapMinMax=None, plotBT=True,
                 plotPolar=True, pd_kwarg=None):
        """

        Parameters
        ----------
        station : str
            The name of the station.
        specie :
        lat0 :
        lon0 :
        folder : param["dirBackTraj"]
        prefix : param["prefix"]
        add_hour : json2arr(param["add_hour"], np.float64)
        resQuality : param["resolutionQuality"][0]
        percentile : json2arr(param["percentile"], np.float64)
        threshold : json2arr(param["threshold"], np.float64)
        concFile :
        dateMin :
        dateMax :
        wfunc : boolean, default True
            Either or not use a weighting function.
        wfunc_type : "manual" or "auto", default "auto"
            Type of weighting function. "auto" is continuous.
        smoothplot : boolean, default True
            Use a gaussian filter to smooth the map plot.
        mapMinMax : dict
            Dictionary of minimun/maximum of lat/lon for the map.
        plotBT : boolean, default True
            Either or not plot all the backtraj in a new axe.
        plotPolar : boolean, default True
            Either or not plot the direction the distribution of the PSCF in a
            polar plot.

        pd_kwarg : dict, optional
            dictionary of option pass to pd.read_csv to read the concentration
            file. By default, pd_kwarg={'index_col'=0, 'parse_date'=['date']}.
        """

        self.station = station
        self.specie = specie
        self.lat0 = lat0
        self.lon0 = lon0
        self.folder = folder
        self.prefix = prefix
        self.add_hour = add_hour
        self.resQuality = resQuality
        self.percentile = percentile
        self.threshold = threshold

        self.mapMinMax = mapMinMax
        self.dateMin = dateMin
        self.dateMax = dateMax

        self.concFile = concFile

        # TODO: properly handle pd_kwarg
        self.data = pd.read_csv(concFile,
                       index_col=0, parse_dates=["date"], **pd_kwarg)

        self.wfunc = wfunc
        self.wfunc_type = wfunc_type
        self.plotBT = plotBT
        self.plotPolar = plotPolar
        self.smoothplot = smoothplot

        self.traj = Basemap(projection='merc',
                            llcrnrlat=mapMinMax["minlat"],
                            urcrnrlat=mapMinMax["maxlat"],
                            llcrnrlon=mapMinMax["minlng"],
                            urcrnrlon=mapMinMax["maxlng"],
                            resolution=resQuality)
    
    # ===== Plot event                          ===============================
    def onclick(self, event):
        """ Find the BT which pass through this cell"""
        ax = plt.gca()
    
        if event.button == 1 and (event.xdata != None and event.ydata != None):
            # x/y to lon/lat
            lon, lat = self.traj(event.xdata, event.ydata, inverse=True)
            lon = np.floor(lon*2)/2
            lat = np.floor(lat*2)/2
            print("Lon/Lat: %.2f / %.2f" %(lon, lat))
            # find all the BT
            lonNorm = np.floor(self.bt["lon"]*2)/2
            latNorm = np.floor(self.bt["lat"]*2)/2
            df = self.bt[((lonNorm == lon) & (latNorm == lat))]
            df = df[:][df["conc"]>self.concCrit]
            for i in np.unique(df["dateBT"]):
                tmp = self.bt[:][self.bt["dateBT"]==i]
                xx,yy = self.traj(tmp["lon"].as_matrix(),tmp["lat"].as_matrix())
                ax.plot(xx,yy, '-',color='0.75')#, marker='.')
                print("date: %.10s | BT: %.13sh | [x]: %s"%(tmp["date"].iloc[0],
                                                            tmp["dateBT"].iloc[0],
                                                            tmp["conc"].iloc[0]))
            print("")
            sys.stdout.flush()
            event.canvas.draw()
        if event.button == 3:
            lon = np.arange(self.mapMinMax["minlng"],
                            self.mapMinMax["maxlng"]+0.01, 0.5) #+0.1 in order to have the max in the array
            lat = np.arange(self.mapMinMax["minlat"], 
                            self.mapMinMax["maxlat"]+0.01, 0.5)
            lon_map, lat_map = np.meshgrid(lon, lat)

            x_map, y_map = self.traj(lon_map, lat_map)

            ax.lines=[]
            pmesh=self.traj.pcolormesh(x_map, y_map, self.PSCF.T, cmap='hot_r')
            self.traj.plot(self.lon0, self.lat0, 'o', color='0.75')
            event.canvas.draw()

    # ===== Load the json file                  ===================================
    # with open(os.path.normpath('parameters/localParamPSCF.json'), 'r') as dataFile:
    #     param=json.load(dataFile)
    # with open(os.path.normpath('parameters/locationStation.json'), 'r') as dataFile:
    #     locStation=json.load(dataFile)
    
    # ===== Initialisation                      ===================================
    # ===== Parameters
    def run(self):
        specie      = self.specie
        lat0, lon0  = float(self.lat0), float(self.lon0)
        folder      = self.folder
        prefix      = self.prefix
        add_hour    = self.add_hour
        resQuality  = self.resQuality
        percentile  = self.percentile
        threshold   = self.threshold
        concFile    = self.concFile
        data        = self.data
        mapMinMax   = self.mapMinMax
        station     = self.station
        traj        = self.traj

        # ===== date

        # date format for the file "YYYY-MM-DD HH:MM"
        dateMin = self.dateMin#pd.Timestamp("-".join(param["dateMin"])).to_pydatetime()
        dateMax = self.dateMax#pd.Timestamp("-".join(param["dateMax"])).to_pydatetime()
        data = data[(data.index > dateMin) & (data.index < dateMax)]
        # extract relevant info
        date = data.index
        conc = data[specie]

        # ===== critical concentration
        if percentile:
            concCrit = sst.scoreatpercentile(conc, percentile)
        elif threshold:
            concCrit = threshold
        else:
            raise ValueError("'percentile' or 'threshold' shoud be specified.'")
        self.concCrit = concCrit
        
        # ===== Extract all back-traj needed        ===================================
        self.bt = extractBackTraj(date, conc, add_hour, folder, prefix,
                             run=72, rainBool=True)
        bt = self.bt

        # ===== convert lon/lat to 0, 0.5, 1, etc
        lon = np.arange(mapMinMax["minlng"], mapMinMax["maxlng"]+0.01, 0.5) #+0.1 in order to have the max in the array
        lat = np.arange(mapMinMax["minlat"], mapMinMax["maxlat"]+0.01, 0.5)
        lon_map, lat_map = np.meshgrid(lon, lat)
        
        ngrid, xedges, yedges = np.histogram2d(bt["lon"],
                                               bt["lat"],
                                               bins=[np.hstack((lon,lon[-1]+0.5)),np.hstack((lat,lat[-1]+0.5))])
        mgrid, xedges, yedges = np.histogram2d(bt["lon"][bt["conc"]>=concCrit],
                                               bt["lat"][bt["conc"]>=concCrit],
                                               bins=[np.hstack((lon,lon[-1]+0.5)),np.hstack((lat,lat[-1]+0.5))])

        n0 = np.where(ngrid!=0)

        PSCF = np.zeros(np.shape(ngrid))
        PSCF[n0] = mgrid[n0]/ngrid[n0]

        trajdensity = np.zeros(np.shape(ngrid))
        trajdensity[n0] = np.log10(ngrid[n0])

        # ===== Weighting function
        if self.wfunc:
            wF = np.zeros(np.shape(ngrid))
            if self.wfunc_type == "manual":
                wFlim=np.array([ float(param["wFlim"][0]), float(param["wFlim"][1]), float(param["wFlim"][2]) ]) *trajdensity.max()
                wFval=np.array([ float(param["wFval"][0]), float(param["wFval"][1]), float(param["wFval"][2]), float(param["wFval"][3]) ])

                wF[ np.where( trajdensity <  wFlim[0]) ]=wFval[0]
                wF[ np.where((trajdensity >= wFlim[0]) & (trajdensity<wFlim[1]))]=wFval[1]
                wF[ np.where((trajdensity >= wFlim[1]) & (trajdensity<wFlim[2]))]=wFval[2]
                wF[ np.where( trajdensity >= wFlim[2]) ]=wFval[3]
            elif self.wfunc_type == "auto":
                #m0 = np.where(mgrid !=0)
                #wF[m0] = np.log(mgrid[m0])/np.log(ngrid.max())
                wF[n0] = np.log(ngrid[n0])/np.log(ngrid.max())

            PSCF = PSCF * wF

        if self.smoothplot:
            PSCF = scipy.ndimage.filters.gaussian_filter(PSCF, 1)
            trajdensity = scipy.ndimage.filters.gaussian_filter(trajdensity, 1)

        self.PSCF = PSCF


        # =========================================================================
        # ===== PLOT PART                       ===================================
        # =========================================================================

        # ===== Plot Back Traj (log(n+1))       ===================================
        # TODO: function
        if self.plotBT:
            figBT=plt.figure()
            mapBT = Basemap(projection='merc',
                        llcrnrlat=mapMinMax["minlat"],
                        urcrnrlat=mapMinMax["maxlat"],
                        llcrnrlon=mapMinMax["minlng"],
                        urcrnrlon=mapMinMax["maxlng"],
                        resolution=resQuality)
            x_BT, y_BT = mapBT(lon_map, lat_map)
            x_station, y_station = mapBT(lon0, lat0)
            cs = mapBT.pcolormesh(x_BT, y_BT, trajdensity.T, cmap='hot_r')

            mapBT.drawcoastlines(color='black')
            mapBT.drawcountries(color='black')
            mapBT.plot(x_station, y_station, 'o', color='0.75')
            plt.title(sation+'\nBack-traj probalility (log(n))')
            figBT.canvas.set_window_title(self.station+"_allBT")
        # ===== Polar plot                      ===================================
        # TODO: function
        if self.plotPolar:
            # change the coordinate system to polar from the station point
            deltalon = lon0-lon
            mesh_deltalon, mesh_lat = np.meshgrid(deltalon, lat)
            mesh_lon, _     = np.meshgrid(lon, lat)
            mesh_deltalon   = toRad(mesh_deltalon)
            mesh_lon        = toRad(mesh_lon)
            mesh_lat        = toRad(mesh_lat)

            a = np.sin(mesh_deltalon) * np.cos(mesh_lat)     
            b = np.cos(lat0*math.pi/180)*np.sin(mesh_lat) - np.sin(lat0*math.pi/180)*np.cos(mesh_lat)*np.cos(mesh_deltalon)
            bearing = np.arctan2(a,b)
            bearing += math.pi/2                        # change the origin: from N to E
            bearing[np.where(bearing<0)] += 2*math.pi   # set angle between 0 and 2pi 
            bearing = bearing.T
        
            # select and count the BT in a given Phi range 
            mPhi=list()
            theta = toRad(np.arange(0,361,22.5))
            mPhi.append( np.sum(mgrid[ np.where( bearing <= theta[1])]))
            for i in range(1, len(theta)-1):
                mPhi.append(np.sum(mgrid[np.where((theta[i]<bearing) & (bearing <=theta[i+1]))]))
            # convert it in percent
            values = mPhi/np.sum(mgrid)*100

            # ===== Plot part
            figPolar=plt.figure()
            xticklabel=['E', 'NE', 'N', 'NO', 'O', 'SO', 'S', 'SE']
        
            axPolar = plt.subplot(111, projection='polar')
            bars = axPolar.bar( theta[:-1], values, width=math.pi/8, align="edge")
            axPolar.xaxis.set_ticklabels(xticklabel)
            axPolar.yaxis.set_ticks(range(0,int(max(values)),5))
        
            plotTitle = "{station}, {specie} > {concCrit}\nFrom {dmin} to {dmax}".format(
                station=station, specie=specie, concCrit=concCrit,
                dmin=min(date).strftime('%Y/%m/%d'), dmax=max(date).strftime('%Y/%m/%d')
            )
            plt.title(plotTitle)
            plt.subplots_adjust(top=0.85, bottom=0.05, left=0.07, right=0.93)
            figPolar.canvas.set_window_title(station+specie+"_windrose")
        # ===== Plot PSCF                       ===================================
        #print(PSCF.max())
        fig=plt.figure()  # keep handle for the onclick function
        ax=plt.subplot(111)



        traj.drawcoastlines()
        traj.drawcountries()
        # traj.drawmapboundary()
        
        x_map, y_map = traj(lon_map, lat_map)
        pmesh        = traj.pcolormesh(x_map, y_map, PSCF.T, cmap='hot_r')
        
        x_station, y_station = traj(lon0, lat0)
        traj.plot(x_station, y_station, 'o', color='0.75')

        plotTitle = "{station}, {specie} > {concCrit}\nFrom {dmin} to {dmax}".format(
            station=station, specie=specie, concCrit=concCrit,
            dmin=min(date).strftime('%Y/%m/%d'), dmax=max(date).strftime('%Y/%m/%d')
        )

        plt.title(plotTitle)
        #plt.colorbar()
            
        cid = fig.canvas.mpl_connect('button_press_event', self.onclick)
        fig.canvas.set_window_title(station+specie)
        # plt.savefig("/run/media/samuel/USB DISK/PSCF_organique/"+param["station"]+"_"+param["species"][specie]+".png")
        plt.show()
        # plt.close()


    # This part is only if you want to run this file via command line.
    # Be sure to have a correct 'localParamPSCF.json' file before running it... otherwhise you will have many error messages.
    # The syntaxe is : python2 PSCF4GUI.py *args
    # where *args is an integer and refer to the specie in 'species' in 'localParamPSCF.json'.
    # If no arg is given, assume that the first specie in 'species' is wanted.
if __name__ == '__main__':
    # plt.interactive(True)
    print("tututu")
    #if len(sys.argv)==1:
    #    p=Process(target=PSCF, args=(0,))
    #    p.start()
    #else:
    #    for i in sys.argv[1:]:
    #        p= Process(target=PSCF, args=(int(i),))
    #        p.start()
