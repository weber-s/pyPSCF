Install
-------

pyPSCF is written in python 3 so the first thing to do is to... well, install
python.

- Linux: it should be already installed. However, depending on your
  distribution, you may have python 2 by default. We do not ensure the
  compatibility.
- Windows/macOS: just use python throught anaconda. It's way more easier. But use
  anaconda for python 3.

Requirements
````````````

Hysplit
'''''''

The GUI has the ability to compute HYSPLIT backtrajectories. To do so, you will
need Hysplit installed.

Hysplit is freely available for Windows, Linux and Mac on the NOAA website 
https://ready.arl.noaa.gov/HYSPLIT.php .

You may also need the NCEP reanalyse GDAS, available in by the NOAA.

Python
''''''

pyPSCF use the following library:

-  matplotlib https://matplotlib.org/
-  numpy https://www.numpy.org/
-  scipy https://www.numpy.org/
-  pandas https://pandas.pydata.org/
-  cartopy http://scitools.org.uk/cartopy/

The first fourth are quite heavily used and easy to install (or already
installed). You can use pip to install them:

    pip install matplotlib numpy scipy pandas

Cartopy
.......

With pip
~~~~~~~~

Cartopy is a bit tricky to install as it requires an extra library: GEOS.
In debian related system, install it via:

    sudo apt install libgeos-3.6.2 libgeos++-dev

Due to some cartopy related issue, you may also need `cython`. Install it via
conda or pip such as:

    pip install cython

With conda/anaconda
~~~~~~~~~~~~~~~~~~~

Cartopy is not included in default anaconda installation. You have to add it
mannually with
    
    conda install -c conda-forge cartopy 

Install latest release version via pip
``````````````````````````````````````

TODO

Install latest release version via pip
``````````````````````````````````````

TODO


GUI Configuration
-----------------

If you use the GUI tool, you need some customization.

Copy the default parameters files in `parameters/` and delete the `_default`
part of their names. You should have the following files in `parameters/`:

    parameters
       ├── SETUP_backTraj.CFG
       ├── localParamBackTraj.json
       ├── localParamBackTraj_default.json
       ├── localParamPSCF.json
       ├── localParamPSCF_default.json
       ├── locationStation.json
       └── locationStation_default.json

That's all. 
Then, run the GUI with `python3 GUI.pyw`.
