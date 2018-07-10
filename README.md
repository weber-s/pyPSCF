[![Documentation Status](https://readthedocs.org/projects/pypscf/badge/?version=latest)](http://pypscf.readthedocs.io/en/latest/?badge=latest) On [readthedocs](https://pypscf.readthedocs.org).

# pyPSCF

The Potential Source Contribution Function is a tool to investigate the
geographical sources origin of chemical species in the atmosphere.

See the UserGuide for detailed information.

# Compute large number of backtrajectories

Under the hood [hysplit](https://ready.arl.noaa.gov/HYSPLIT.php) is used to
compute backtrajectories. This GUI allows you to compute easily large number of
backtrajectories given a starting date and an end date.

![backtraj](static/img/BackTrajGUI.png)

# Install

Simply clone this repo if you are used to git:

    git clone https://gricad-gitlab.univ-grenoble-alpes.fr/webersa/pyPSCF.git

or download the zipped archive.

You will need python and some other dependancies. See the
[docs](https://pypscf.readthedocs.org).

# Compute PSCF 

## Select parameters 

The second tab of the GUI are the PSCF parameters.

![PSCF](static/img/PSCF.png)

## Output

A figure will show up with the PSCF in colorscale. You can clic on a gridcell to
see all the backtrajectories that pass through this gridcell.

![example](static/img/SeaSalt_BT.png)

# Contribution

This GUI is an adapted GUI from the game "The Battle For Westnoth", developed by
Elvish_Hunter, 2014-2015, under the GNU GPL v2 license.

Original PSCF script: Jean-Eudes PETIT 

New PSCF script and GUI tools : Samuel WEBER

Icons are taken from the Tango Desktop Project (http://tango.freedesktop.org)
and are released in the Public Domain.
