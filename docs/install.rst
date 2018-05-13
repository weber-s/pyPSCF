Install
-------

pyPSCF is written in python 3 so the first thing to do is to... well, install
python.

- Linux: it should be already installed. However, depending on your
  distribution, you may have python 2 by default. We do not ensure the
  compatibility.
- Windows: just use python throught anaconda. It's way more easier. But use
  anaconda for python 3.
- macOS: I do not known. If someone do, please edit this line :).

Requirements
~~~~~~~~~~~~

Hysplit
^^^^^^^

The GUI has the ability to compute HYSPLIT backtrajectories. To do so, you will
need Hysplit installed.

Python
^^^^^^

pyPSCF use the following library:

-  matplotlib https://matplotlib.org/
-  numpy https://www.numpy.org/
-  scipy https://www.numpy.org/
-  pandas https://pandas.pydata.org/
-  cartopy http://scitools.org.uk/cartopy/

The first fourth are quite heavily used and easy to install (or already
installed). You can use pip to install them:

    pip install matplotlib numpy scipy pandas

Cartopy is a bit tricky to install as it requires an extra library: GEOS.
In debian related system, install it via:

    sudo apt install libgeos-3.6.2 libgeos++-dev

Due to some cartopy related issue, you may also need `cython`. Install it via
conda or pip such as:

    pip install cython

Install latest release version via pip
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
TODO
