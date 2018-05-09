from pyPSCF import *

station = "OPE"
specie = "Levo"
lat0=48.53
lon0=5.50
dateMax = "2014"
dateMin = "2010"
prefix = "traj_OPE_"
hourinthepast = 72
concFile = "/home/samuel/Documents/IGE/PSCF/concentrations/OPE.csv"
specie = "Levo"
station = "OPE"
mapMinMax = {"lonmin": -10.0, "lonmax": 35.0, "latmin": 32.5, "latmax": 64.0}
cutWithRain = True 
wfunc = True
wfunc_type = "auto" 
add_hour = [-6, -3, 0, 3, 6] 
percentile = 75 
threshold = 0.4
resQuality = "l"
plotBT = False
plotPolar = False
folder = "/home/samuel/Documents/IGE/PSCF/retrotrajectoires/OPE/"
smoothplot = True
pd_kwarg = {"sep": ","}

model = PSCF(station=station, specie=specie, lat0=lat0, lon0=lon0,
             folder=folder, prefix=prefix, add_hour=add_hour,
             resQuality=resQuality, percentile=percentile, threshold=threshold,
             concFile=concFile, dateMin=dateMin, dateMax=dateMax, wfunc=wfunc,
             wfunc_type=wfunc_type, smoothplot=smoothplot, mapMinMax=mapMinMax,
             cutWithRain=cutWithRain, hourinthepast=hourinthepast,
             plotBT=plotBT, plotPolar=plotPolar, pd_kwarg=pd_kwarg)

model.run()
