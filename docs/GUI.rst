How to run the GUI
==================

There are several way to run the GUI, depending on what you are familiar with.

* From the terminal: navigate where the `GUI.pyw` file is, then enter
    
    python3 GUI.pyw

* Using spyder/ipython

    %run GUI.pyw

* Graphically: simply double click on `GUI.pyw`. It may work. Maybe.

If it doesn't start, ensure that you are running python 3 and not python 2.

Compute the back-trajectories
=============================

Hysplit
-------

The back-trajectories have to be computed before running the PSCF script. 
We use here the Hysplit program from the NOAA. 
As Hysplit is a relatively big software with many option and configuration, we
developed a tool to compute the back trajectory in a easy way.  However, you
still need the Hysplit program. 
You can found it at http://ready.arl.noaa.gov/HYSPLIT.php.

GUI description
---------------

.. image:: ../static/img/BackTrajGUI.png

Once the script starts, you should see the window presented in figure. 
Navigate to the *Back-trajectory* tab on the top if it is not already open.
This window presents the different parameters use to compute the back-trajectories. 
Let's describe each of its field.

* Button frame

  * *Run Back-traj*: Save the parameters show in this tab in
    *parameters/localParamBackTraj.json* then compute the back-trajectories with
    theses parameters.
  * *Save BackTraj*: Save the parameters in the
    *parameters/localParamBackTraj.json* file without running the computation.
  * *Exit*: Quit the GUI without saving the parameters.

* *Meteo (GDAS) directory*: select the path to the GDAS files. GDAS is a file
  format uses to store meteorological data and are freely available from the
  `NOAA website <http://ready.arl.noaa.gov/archives.php>`_ or `ftp
  <ftp://arlftp.arlhq.noaa.gov/pub/archives/gdas1/>`_.
* *Hysplit directory*: select the root path of the Hysplit directory's
  installation. It should contain the subdirectories *working, exec,
  script* etc.  
* *Output directory*: select where the back-trajectories files will be save.

* *Station frame*

  * *Station*: select the desired reference point. If the station is not in
    the list you have to add yourself the station in the
    `parameters/locationStation.json` file.
  * *Longitude/Latitude*: enter the longitude/latitude of the station. It should
    be updated automatically with the selection of the station.
  * *Altitude*: enter the altitude (in meter from the surface) of the
    back-trajectory starting point.

..
.. \paragraph{Date frame}
.. Enter from when to when the back-trajectories will be computed.
..
.. \paragraph{Back-traj parameters frame}
.. By default, for each back-trajetory, the value are save in the file each hour.
.. See the hysplit user guide for details.
.. \begin{description}
..     \item[Time for the back-trajectory [h{]}] Enter for how long the
..         back-trajectory will be computed (i.e.\ up to when in the past in hours).
..     \item[Step between 2 starting back-trajectories [h{]}] Enter the time between 2 saves in the
..         output file. Minimum is 1 hour. 
.. \end{description}
..
.. \paragraph{CPU frame} As the program is parallelizable, enter how many core should compute the back-trajectories. 
.. By default is your number of CPU minus 1. 
.. Beware! As the computation may take a long time, choosing your exact number of CPU is not recomended!
.. Otherwise you won't be able to do anything else during the computation.
..
.. \section{PSCF computation}
.. %\subsection{GUI description}
.. \begin{figure}[h]
..     \centering
..     \includegraphics[width=\textwidth]{PSCF.png}
..     \caption{GUI of the PSCF script}
..     \label{fig:PSCF}
.. \end{figure}
.. Navigate to the \emph{PSCF} tab, you should see the window presented in figure~\ref{fig:PSCF}. 
.. This window present the different parameters use to compute the {PSCF}. 
.. Let's describe each of its field.
..
.. \paragraph{Button}
.. \begin{description}
..     \item[Run PSCF] Save the parameters in
..     \texttt{parameters/localParamPSCF.json} then run the PSCF with theses
..     parameters. It will print the desired plot.
..     \item[Save PSCF] Save the parameters in the \texttt{parameters/localParamPSCF.json}
..         file without running the PSCF. 
..     \item[Exit] Quit the program without saving the parameters.
.. \end{description}
..
.. \paragraph{Back-trajectory directory}
.. Select the directory where the back-trajectories are stored. The path is red if
.. it doesn't exist (as you can see in the screenshot).
..
.. \paragraph{Concentration file}
.. Select the concentration file. It must be a coma separated value file (CSV),
.. with the delimiter ``;''. The first raw must contain the name of each specie.
.. The path is red if it doesn't exist (as you can see in the screenshot).
..
.. \paragraph{Station frame} 
.. Select the studied station. If your station is not listed you have to complete
.. the \texttt{parameters/locationStation.json} file (explain in
.. section~\ref{sec:locationStation} hereafter). The back-trajectory prefix and
.. latitude/longitude should update automatically. If the back-trajectories are
.. save with another prefix, edit the ``Back-traj prefix'' field.
..
.. \paragraph{Back Trajectory frame}
.. \begin{description}
..     \item[Back-trajectory [h{]}] Specify how long the back-trajectory have to be
..         (in hour).
..     \item[Add hour] Add back-trajectory for each observation. For example if an
..         acquisition starts at 00:00 and ends and 23h59 you may want to take into
..         acount the back-trajectories at 00h, but also 03h, 06h, 09h, \dots 18h and 24h.
..         To do so, simply add the hours you want. It must be an array (i.e.\ start with a
..         ``$[$'' and end with a ``$]$'', each value separated by a coma).
..     \item[Rain] Check the ``Cut when it's rainning'' box if you want to cut the
..         back-trajectory with the rain.
.. \end{description}
..
.. \paragraph{Weighting function frame}
.. Check the box if you want to use a weighting function.
.. \begin{description}
..     \item[User defined] Let the user defined the weighting function. ``d'' means
..         the logarithm of back-trajectory density. Select the desired threshold
..         and the associated weighting value.
..     \item[Auto] A continuous weighting function is uses and is defined as follows:
..         \begin{align}
..             WF_{ij} &= \frac{\log{(N_{ij})}}{\log{(\max{(N)})}}
..             \label{eq:WFauto}
..         \end{align}
.. \end{description}
..
.. \paragraph{Species frame}
.. \begin{description}
..     \item[Specie(s) to study] Enter the name of the specie(s) you want to study.
..         It must match the first line of the concentration file. Multiple species
..         can be indicated, delimited by ``;''.
..     \item[Use of the percentile or an arbitraty threshold] Select the way you want
..         to define the threshold to keep a back-trajectory in the M matrix. If
..         you want the X$^{th}$ percentil of the specie check the box and enter the
..         desired percentil. If you prefer an arbitrary threshold uncheck the box
..         and enter a threshold. Both of the percentil or the aribtray threshold
..         must be an array (i.e.\ starts with a ``$[$'' and ends with a ``$]$'', each
..         value separated by a coma).
..         You can enter several threshold or percentil. In this case the first
..         percentil/threshold is uses for the first specie, the second for the
..         second specie, etc. If only one percentile/threshold is specified it is
..         use for all the species.
.. \end{description}
..
.. \paragraph{Date frame}
.. Choose from when to when the PSCF will be computed. It may be useful to
.. select a subset of the concentration file without create a new file.
..
.. \paragraph{Miscellaneous frame}
.. \begin{description}
..     \item[Longitude/Latitude] Enter the min/max latitude and longitude for the plot part.
..     \item[Plot back-traj] Plot the N matrix, i.e. all the back-trajectory, in a
..         other figure.
..     \item[Plot polar plot] Plot a polar plot indicated the number of cell of M there 
..         are in the N, NW, W, SW, S, SE, E, NE quarters, in a other figure.
..     \item[Smooth the result] Use a gaussian filter to smooth the result.
..     \item[Background resolution] Select the resolution of the map background.
..         Higher resolution dataset is much slower to draw.  
..         Coastline or lake with an area respectively smaller than 10000, 1000,
..         100, 10, 1 km$^2$ for resolution crude, low, intermediare, high, full
..         will not be plotted. 
..         See the matplolib Basemap module\footnote{site:
..             \url{http://matplotlib.org/basemap/api/basemap_api.html\#module-mpl_toolkits.basemap}
..         } for details.
.. \end{description}
..
.. \section{Plot manipulation}
.. \subsection{See trajectories} 
.. A \textbf{left-clic} on the map will print all the back-trajectories that passed through
.. this grid-cell.  
.. A \textbf{right-clic} clear all the previous plotted back-trajectories. 
.. If you start the script from a terminal, it will also print in the terminal the
.. associated concentrations and days as shows in figure~\ref{fig:leftclic}.
..
.. \begin{figure}[h!]
..     \centering
..     \begin{subfigure}[b]{0.55\textwidth}
..         \includegraphics[width=\textwidth]{SeaSalt_BT.png}
..         \caption{Map view}
..     \end{subfigure}
..     {}
..     \begin{subfigure}[b]{0.43\textwidth}
..         \includegraphics[width=\textwidth]{Terminal_Output.png}
..         \caption{Terminal output}
..     \end{subfigure}
..     \caption{A left-clic on the map near the ``Massif Central'' at 45\degree 00'
..     N/2\degree 00' E highlights 10 back-trajectories that passed through the
.. selected grid-cell.}
..     \label{fig:leftclic}
.. \end{figure}
..
.. \subsection{Save plot} 
.. As the script uses the matplotlib module, you can save the figure in the same
.. way as all matplotlib figures by clicking the diskette icon. You can choose the
.. format you want (pdf, png, svg, etc.).
..
..
.. \section{Add or modify a station}\label{sec:locationStation}
.. If you want to change the list of the stations (add, remove or modify an
.. existing one), you have to edit the \texttt{parameters/locationSation.json} file.
..
.. \paragraph{Manually}
.. You can mannualy open the \texttt{parameters/locationStation.json} with a text
.. editor (NotePad, WordPad, Gedit, VIM, etc.) and add your station between the two
.. brackets as follow:
.. \begin{verbatim}
.. {
..     ``STATION_NAME_1'': [``latitude'', ``longitude'', ``altitude''],
..     ``STATION_NAME_2'': [``latitude'', ``longitude'', ``altitude''],
..     ...
..     ``STATION_NAME_n'': [``latitude'', ``longitude'', ``altitude'']
.. }
.. \end{verbatim}
.. Be \emph{sure} that all lines terminate with a coma but not the last one!
.. Otherwith an error will be raised.  The longitude/latitude are in degree.
..
.. \paragraph{Using the GUI}
.. Navigate to the \emph{Stations param.} tab. You should see the GUI as in
.. figure~\ref{fig:editStation}.
..
.. To modify an already existing station, select it, modify the latitude/longitude
.. and the default altitude for the back-trajectory computation then click on ``Save''.
..
.. To delete an already existing station, select it and click on ``Delete''.
.. Beware, this is unrecoverable.
..
.. To add a station, fill the Station name, the latitude/longitude and the default
.. altitude for the back-trajectory computation then click on ``Save''.
..
.. \begin{figure}[h]
..     \centering
..     \includegraphics[width=\textwidth]{ModifStationGUI}
..     \caption{GUI to edit, delete or add a station.}
..     \label{fig:editStation}
.. \end{figure}
..
.. %%fake section Bibliography
.. %\bibliography{}
.. %\bibliographystyle{unsrtnat}
..
.. \end{document}
..
..
