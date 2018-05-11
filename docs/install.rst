Install
-------

Requirements
~~~~~~~~~~~~

pyPSCF use the following library:

-  matplotlib https://matplotlib.org/
-  numpy https://www.numpy.org/
-  scipy https://www.numpy.org/
-  pandas https://pandas.pydata.org/
-  cartopy http://scitools.org.uk/cartopy/

The first fourth are quite heavily use and easy to install (or already
install). You can use pip to install them:

    pip install matplotlib numpy scipy pandas

Cartopy is a bit tricky to install as it requires an extra library: GEOS.
In debian related system, install it via:

    sudo apt install libgeos-3.6.2 libgeos++-dev

Due to some cartopy related issue, you may also need `cython`. Install it via
conda or pip such as:

    pip install cython

Installation
~~~~~~~~~~~~


Install latest release version via pip
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
TODO
