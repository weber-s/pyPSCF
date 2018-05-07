# -*-coding:Utf-8 -*
import sys, os
import datetime as dt
import numpy as np
import json
# import scipy
from scipy.ndimage.filters import gaussian_filter
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
# from scipy import signal
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


class PSCF:
    """
    The main PSCF function. Compute the PSCF according to the parameters in 'localParamPSCF.json'.
    The argument is the rank of the specie in the "species" in the 'localParamPSCF.json' file.
    If no argument is given, assume that there is only one specie and takes the first one.
    """
    def __init__(self, station, specie, lat0, lon0, folder, prefix, add_hour, resQuality,
                 percentile, threshold, concFile, dateMin, dateMax, wfunc=True,
                 wfunc_type="auto", smoothplot=True, mapMinMax=None,
                 cutWithRain=True, hourinthepast=72, plotBT=True, plotPolar=True, pd_kwarg=None):
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
        concFile : str, path.
            The path to the concentration file.
        dateMin :
        dateMax :
        wfunc : boolean, default True
            Either or not use a weighting function.
        wfunc_type : "manual" or "auto", default "auto"
            Type of weighting function. "auto" is continuous.
        mapMinMax : dict
            Dictionary of minimun/maximum of lat/lon for the map.
        cutWithRain : boolean, default True
            Either or not cut the backtrajectory to the last rainning date.
        hourinthepast : integer, default 72
            Number of hour considered for the backtrajectory life.
        smoothplot : boolean, default True
            Use a gaussian filter to smooth the map plot.
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
        

        # TODO: properly handle pd_kwarg
        self.data = pd.read_csv(concFile,
                       index_col=0, parse_dates=["date"], **pd_kwarg)
        
        self.wfunc = wfunc
        self.wfunc_type = wfunc_type
        self.plotBT = plotBT
        self.plotPolar = plotPolar
        self.smoothplot = smoothplot

        self.cutWithRain = cutWithRain
        self.hourinthepast = hourinthepast

        self.map = Basemap(projection='merc',
                            llcrnrlat=mapMinMax["minlat"],
                            urcrnrlat=mapMinMax["maxlat"],
                            llcrnrlon=mapMinMax["minlng"],
                            urcrnrlon=mapMinMax["maxlng"],
                            resolution=resQuality)
    

    def toRad(self, x):
        return x*math.pi/180
    # ===== Plot event                          ===============================
    def onclick(self, event, plotType):
        """ Find the BT which pass through the clicked cell."""
        ax = plt.gca()
    
        if event.button == 1 and (event.xdata != None and event.ydata != None):
            # x/y to lon/lat
            lon, lat = self.map(event.xdata, event.ydata, inverse=True)
            lon = np.floor(lon*2)/2
            lat = np.floor(lat*2)/2
            print("Lon/Lat: %.2f / %.2f" %(lon, lat))
            # find all the BT
            lonNorm = np.floor(self.bt["lon"]*2)/2
            latNorm = np.floor(self.bt["lat"]*2)/2
            df = self.bt[((lonNorm == lon) & (latNorm == lat))]
            if plotType == "PSCF":
                df = df[:][df["conc"]>self.concCrit]
            for i in np.unique(df["dateBT"]):
                tmp = self.bt[:][self.bt["dateBT"]==i]
                xx,yy = self.map(tmp["lon"].as_matrix(),tmp["lat"].as_matrix())
                ax.plot(xx,yy, '-',color='0.75')#, marker='.')
                print("date: %.10s | BT: %.13sh | [x]: %s"%(tmp["date"].iloc[0],
                                                            tmp["dateBT"].iloc[0],
                                                            tmp["conc"].iloc[0]))
            print("")
            sys.stdout.flush()
            event.canvas.draw()
        if event.button == 3:
            # lon = np.arange(self.mapMinMax["minlng"],
            #                 self.mapMinMax["maxlng"]+0.01, 0.5) #+0.1 in order to have the max in the array
            # lat = np.arange(self.mapMinMax["minlat"], 
            #                 self.mapMinMax["maxlat"]+0.01, 0.5)
            # lon_map, lat_map = np.meshgrid(lon, lat)

            x_map, y_map = self.map(self.lon_map, self.lat_map)

            ax.lines=[]

            if plotType == "allBT":
                var = self.trajdensity_ 
            elif plotType == "PSCF":
                var = self.PSCF_
            else:
                raise ValueError("`plotType` must be in ['allBT', 'PSCF']")

            if self.smoothplot:
                var = gaussian_filter(var, 1)

            pmesh=self.map.pcolormesh(x_map, y_map, var.T, cmap='hot_r')
            x_station, y_station = self.map(self.lon0, self.lat0)
            self.map.plot(x_station, y_station, 'o', color='0.75')
            event.canvas.draw()

    def extractBackTraj(self):
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
        for date, conc in zip(self.date, self.conc):
            # find all back traj for the date d
            for hour in self.add_hour:
                # open back traj file
                name = self.prefix + aammddhh(date+dt.timedelta(hours=hour))
                datafile=os.path.join(self.folder, name)

                if not os.path.isfile(datafile):
                    print('Back-trajectory {} file is missing'.format(name))
                    continue
                else:
                    # add the lon/lat of the BT
                    nb_line_to_skip = linecache.getline(datafile, 1).split()
                    nb_line_to_skip = int(nb_line_to_skip[0])
                    meteo_idx = linecache.getline(datafile, nb_line_to_skip+4).split()
                    idx_names = ["a", "b", "year", "month", "day", "hour", "c",
                                 "d", "run", "lat", "lon", "alt"]
                    idx_names = np.hstack((idx_names, meteo_idx[1:]))

                    traj = pd.read_table(datafile,
                                         delim_whitespace = True,
                                         header = None,
                                         names = idx_names,
                                         skiprows = nb_line_to_skip+4,
                                         nrows = self.hourinthepast)
                    lat = traj["lat"]
                    lon = traj["lon"]
                    rain = traj["RAINFALL"]

                    # if it was raining at least one time, we cut it
                    if self.cutWithRain and any(rain>0):
                        idx_rain = np.where(rain!=0)[0][0]
                        lat = lat[:idx_rain]
                        lon = lon[:idx_rain]

                    dftmp = pd.DataFrame(data={"date":date,
                                               "dateBT":date+dt.timedelta(hours=hour),
                                               "conc":conc,
                                               "lon":lon,
                                               "lat":lat})
                    
                    df = pd.concat([df,dftmp])

        return df


    def run(self):
        specie      = self.specie
        percentile  = self.percentile
        threshold   = self.threshold
        data        = self.data
        mapMinMax   = self.mapMinMax
        station     = self.station

        # extract relevant info
        # date format for the file "YYYY-MM-DD HH:MM"
        data = data[(data.index > self.dateMin) & (data.index < self.dateMax)]

        self.date = data.index

        self.conc = data[specie]

        # ===== critical concentration
        if percentile:
            concCrit = sst.scoreatpercentile(self.conc, percentile)
        elif threshold:
            concCrit = threshold
        else:
            raise ValueError("'percentile' or 'threshold' shoud be specified.'")
        self.concCrit = concCrit
        
        # ===== Extract all back-traj needed        ===========================
        self.bt = self.extractBackTraj()

        # ===== convert lon/lat to 0, 0.5, 1, etc
        # +0.1 in order to have the max in the array
        self.lon = np.arange(mapMinMax["minlng"], mapMinMax["maxlng"]+0.01, 0.5) 
        self.lat = np.arange(mapMinMax["minlat"], mapMinMax["maxlat"]+0.01, 0.5)
        self.lon_map, self.lat_map = np.meshgrid(self.lon, self.lat)
        
        ngrid, xedges, yedges = np.histogram2d(self.bt["lon"],
                                               self.bt["lat"],
                                               bins=[
                                                   np.hstack((self.lon,
                                                              self.lon[-1]+0.5)),
                                                   np.hstack((self.lat,
                                                              self.lat[-1]+0.5))
                                               ])
        maskgtconcCrit = self.bt["conc"]>=concCrit
        mgrid, xedges, yedges = np.histogram2d(self.bt.loc[maskgtconcCrit,"lon"],
                                               self.bt.loc[maskgtconcCrit,"lat"],
                                               bins=[
                                                   np.hstack((self.lon,
                                                              self.lon[-1]+0.5)),
                                                   np.hstack((self.lat,
                                                              self.lat[-1]+0.5))
                                               ])

        not0 = np.where(ngrid!=0)

        PSCF = np.zeros(np.shape(ngrid))
        PSCF[not0] = mgrid[not0]/ngrid[not0]

        trajdensity = np.zeros(np.shape(ngrid))
        trajdensity[not0] = np.log10(ngrid[not0])

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
                wF[not0] = np.log(ngrid[not0])/np.log(ngrid.max())

            PSCF = PSCF * wF

        self.ngrid_ = ngrid
        self.mgrid_ = mgrid 
        self.PSCF_ = PSCF
        self.trajdensity_ = trajdensity


    def plot_backtraj(self):
        """Plot a map of all trajectories.
        """
        figBT=plt.figure()
        ax=plt.subplot(111)

        if self.smoothplot:
            trajdensity = gaussian_filter(self.trajdensity_, 1)
        else:
            trajdensity = self.trajdensity_

        self.map.drawcoastlines(color='black')
        self.map.drawcountries(color='black')

        x_BT, y_BT = self.map(self.lon_map, self.lat_map)
        pmesh = self.map.pcolormesh(x_BT, y_BT, trajdensity.T, cmap='hot_r')

        x_station, y_station = self.map(self.lon0, self.lat0)
        self.map.plot(x_station, y_station, 'o', color='0.75')

        plotTitle = "{station}\nBacktrajectories probability (log(n))".format(
            station=self.station
        )
        plt.title(plotTitle)


        cid = figBT.canvas.mpl_connect('button_press_event', 
                                       lambda event: self.onclick(event, "allBT"))
        figBT.canvas.set_window_title(self.station+"_allBT")

    def plot_PSCF_polar(self):
        """ Plot a polar plot of the PSCF
        """
        # change the coordinate system to polar from the station point
        deltalon = self.lon0 - self.lon
        mesh_deltalon, mesh_lat = np.meshgrid(deltalon, self.lat)
        mesh_lon, _     = np.meshgrid(self.lon, self.lat)
        mesh_deltalon   = self.toRad(mesh_deltalon)
        mesh_lon        = self.toRad(mesh_lon)
        mesh_lat        = self.toRad(mesh_lat)

        a = np.sin(mesh_deltalon) * np.cos(mesh_lat)     
        b = np.cos(self.lat0*math.pi/180)*np.sin(mesh_lat) \
            - np.sin(self.lat0*math.pi/180)*np.cos(mesh_lat)*np.cos(mesh_deltalon)
        bearing = np.arctan2(a, b)
        bearing += math.pi/2                        # change the origin: from N to E
        bearing[np.where(bearing<0)] += 2*math.pi   # set angle between 0 and 2pi 
        bearing = bearing.T
        
        # select and count the BT in a given Phi range 
        mPhi = list()
        theta = self.toRad(np.arange(0,361,22.5))
        mPhi.append( np.sum( self.mgrid_[ np.where(bearing <= theta[1]) ] ))
        for i in range(1, len(theta)-1):
            mPhi.append(np.sum(self.mgrid_[np.where((theta[i]<bearing) & (bearing <=theta[i+1]))]))
        # convert it in percent
        values = mPhi/np.sum(self.mgrid_)*100

        # ===== Plot part
        figPolar=plt.figure()
        xticklabel=['E', 'NE', 'N', 'NO', 'O', 'SO', 'S', 'SE']
    
        axPolar = plt.subplot(111, projection='polar')
        bars = axPolar.bar( theta[:-1], values, width=math.pi/8, align="edge")
        axPolar.xaxis.set_ticklabels(xticklabel)
        axPolar.yaxis.set_ticks(range(0,int(max(values)),5))
    
        plotTitle = "{station}, {specie} > {concCrit}\nFrom {dmin} to {dmax}".format(
            station=self.station, specie=self.specie, concCrit=self.concCrit,
            dmin=min(self.date).strftime('%Y/%m/%d'), 
            dmax=max(self.date).strftime('%Y/%m/%d')
        )
        plt.title(plotTitle)
        plt.subplots_adjust(top=0.85, bottom=0.05, left=0.07, right=0.93)
        figPolar.canvas.set_window_title(self.station+self.specie+"_windrose")

    def plot_PSCF(self):
        """Plot the PSCF map.
        """
        fig=plt.figure()  # keep handle for the onclick function
        ax=plt.subplot(111)
        
        if self.smoothplot:
            PSCF = gaussian_filter(self.PSCF_, 1)
        else:
            PSCF = self.PSCF_

        self.map.drawcoastlines()
        self.map.drawcountries()
        
        x_map, y_map = self.map(self.lon_map, self.lat_map)
        pmesh        = self.map.pcolormesh(x_map, y_map, PSCF.T, cmap='hot_r')
        
        x_station, y_station = self.map(self.lon0, self.lat0)
        self.map.plot(x_station, y_station, 'o', color='0.75')

        plotTitle = "{station}, {specie} > {concCrit}\nFrom {dmin} to {dmax}".format(
            station=self.station, specie=self.specie,
            concCrit=self.concCrit.round(5),
            dmin=min(self.date).strftime('%Y/%m/%d'),
            dmax=max(self.date).strftime('%Y/%m/%d')
        )
        plt.title(plotTitle)
            
        cid = fig.canvas.mpl_connect('button_press_event',
                                     lambda event: self.onclick(event, "PSCF"))
        fig.canvas.set_window_title(self.station+self.specie)


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
