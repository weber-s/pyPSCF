#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import datetime
import calendar
import os, sys, json
from multiprocessing import Process, cpu_count
# sys.version_info checks the interpreter version
# this is used to have a script that can run on both Python2 and Python3
# not that useful until the mainline tools are updated, but still...
if sys.version_info.major >= 3:
    import queue
    # tkinter modules
    from tkinter import *
    from tkinter.messagebox import *
    from tkinter.filedialog import *
    # ttk must be called last
    from tkinter.ttk import *
else: # we are on Python 2
    import Queue
    # tkinter modules
    from Tkinter import *
    from tkMessageBox import *
    from tkFileDialog import *
    # ttk must be called last
    from ttk import *

from modules.backTraj4GUI import *

class EntryContext(Entry):
    def __init__(self,parent,**kwargs):
        """An enhanced Entry widget that has a right-click menu
Use like any other Entry widget"""
        if sys.version_info.major>=3:
            super().__init__(parent,**kwargs)
        else:
            Entry.__init__(self,parent,**kwargs)
        # on Mac the right button fires a Button-2 event, or so I'm told
        # some mice don't even have two buttons, so the user is forced
        # to use Command + the only button
        # bear in mind that I don't have a Mac, so this point may be bugged
        # bind also the context menu key, for those keyboards that have it
        # that is, most of the Windows and Linux ones (however, in Win it's
        # called App, while on Linux is called Menu)
        # Mac doesn't have a context menu key on its keyboards, so no binding
        # bind also the Shift+F10 shortcut (same as Menu/App key)
        # the call to tk windowingsystem is justified by the fact
        # that it is possible to install X11 over Darwin
        # finally, bind the "select all" key shortcut
        # again, Mac uses Command instead of Control
        windowingsystem = self.tk.call('tk', 'windowingsystem')
        if windowingsystem == "win32": # Windows, both 32 and 64 bit
            self.bind("<Button-3>",self.on_context_menu)
            self.bind("<KeyPress-App>",self.on_context_menu)
            self.bind("<Shift-KeyPress-F10>",self.on_context_menu)
            # for some weird reason, using a KeyPress binding to set the selection on
            # a readonly Entry or disabled Text doesn't work, but a KeyRelease does
            self.bind("<Control-KeyRelease-a>", self.on_select_all)
        elif windowingsystem == "aqua": # MacOS with Aqua
            self.bind("<Button-2>",self.on_context_menu)
            self.bind("<Control-Button-1>",self.on_context_menu)
            self.bind("<Command-KeyRelease-a>", self.on_select_all)
        elif windowingsystem == "x11": # Linux, FreeBSD, Darwin with X11
            self.bind("<Button-3>",self.on_context_menu)
            self.bind("<KeyPress-Menu>",self.on_context_menu)
            self.bind("<Shift-KeyPress-F10>",self.on_context_menu)
            self.bind("<Control-KeyRelease-a>", self.on_select_all)
    def on_context_menu(self,event):
        if str(self.cget('state')) != DISABLED:
            ContextMenu(event.x_root,event.y_root,event.widget)
    def on_select_all(self,event):
        self.select_range(0,END)

class SelectDirectory(LabelFrame):
    def __init__(self,parent,textvariable=None, title="Directory", **kwargs):
        """A subclass of LabelFrame sporting a readonly Entry and a Button with a folder icon.
It comes complete with a context menu and a directory selection screen"""
        if sys.version_info.major>=3:
            super().__init__(parent,text=title,**kwargs)
        else:
            LabelFrame.__init__(self,parent,text=title,**kwargs)
        self.textvariable=textvariable
        self.dir_entry=EntryContext(self,
                                    width=40,
                                    textvariable=self.textvariable)
        self.dir_entry.pack(side=LEFT,
                            fill=BOTH,
                            expand=YES)
        self.dir_button=Button(self,
                               image=ICONS['browse'],
                               compound=LEFT,
                               text="Browse...",
                               command=self.on_browse_dir)
        self.dir_button.pack(side=LEFT)
        self.clear_button=Button(self,
                                 image=ICONS['clear16'],
                                 compound=LEFT,
                                 text="Clear",
                                 command=self.on_clear)
        self.clear_button.pack(side=LEFT)
    def on_browse_dir(self):
        # if the user already selected a directory, try to use it
        current_dir=self.textvariable.get()
        if os.path.exists(current_dir):
            directory=askdirectory(initialdir=current_dir)
        # otherwise attempt to detect the user's userdata folder
        else:
            # os.path.expanduser gets the current user's home directory on every platform
            if sys.platform=="win32":
                # get userdata directory on Windows
                # it assumes that you choose to store userdata in the My Games directory
                # while installing Wesnoth
                userdata=os.path.join(os.path.expanduser("~"),
                                      "Documents")
            elif sys.platform.startswith("linux"): # we're on Linux; usually this string is 'linux2'
                userdata=os.path.join(os.path.expanduser("~"),
                                      "Documents")
            elif sys.platform=="darwin": # we're on MacOS
                # bear in mind that I don't have a Mac, so this point may be bugged
                userdata=os.path.join(os.path.expanduser("~"),
                                      "Library")
            else: # unknown system; if someone else wants to add other rules, be my guest
                userdata="."

            if os.path.exists(userdata): # we may have gotten it wrong
                directory=askdirectory(initialdir=userdata)
            else:
                directory=askdirectory(initialdir=".")

        if directory:
            # use os.path.normpath, so on Windows the usual backwards slashes are correctly shown
            self.textvariable.set(os.path.normpath(directory))
    def on_clear(self):
        self.textvariable.set("")


class MainFrame(Frame):
    def __init__(self,parent):
        self.parent=parent
        if sys.version_info.major>=3:
            self.queue=queue.Queue()
            super().__init__(parent)
        else:
            self.queue=Queue.Queue()
            Frame.__init__(self,parent)
        # Import local Param from the JSON file
        with open('parameters'+os.sep+'localParamBackTraj.json', 'r') as dataFile:
            param=json.load(dataFile)
        with open('parameters'+os.sep+'locationStation.json', 'r') as dataFile:
            locStation=json.load(dataFile)

        self.grid(sticky=E+W+N+S)
        self.buttonBox=Frame(self)
        self.buttonBox.grid(row=0,
                            columnspan=2,
                            sticky=E+W+S+N)
        self.about_button=Button(self.buttonBox,
                                 text="About...",
                                 image=ICONS['about'],
                                 compound=LEFT,
                                 command=self.on_about)
        self.about_button.pack(side=LEFT, padx=5, pady=5)
        self.run_button=Button(self.buttonBox,
                               text="Run Back-traj",
                               image=ICONS['run'],
                               compound=LEFT,
                               width=15, # to avoid changing size when callback is called
                               command=self.on_run)
        self.run_button.pack(side=LEFT, padx=5, pady=5)
        self.save_button=Button(self.buttonBox,
                                 text="Save param",
                                 image=ICONS['save'],
                                 compound=LEFT,
                                 command=self.on_save)
        self.save_button.pack(side=LEFT, padx=5, pady=5)
        self.exit_button=Button(self.buttonBox,
                                text="Exit",
                                image=ICONS['exit'],
                                compound=LEFT,
                                command=parent.destroy)
        self.exit_button.pack(side=RIGHT, padx=5, pady=5)
        #Directory
        self.dirGDAS=StringVar()
        self.dirGDAS.set(param["dirGDAS"])
        self.dirGDASSelect=SelectDirectory(self, textvariable=self.dirGDAS, title="Meteo (GDAS) directory")
        self.dirGDASSelect.grid(row=1, column=0, columnspan=2, sticky=E+W, padx=5, pady=5)
        self.dirHysplit=StringVar()
        self.dirHysplit.set(param["dirHysplit"])
        self.dirHysplitSelect=SelectDirectory(self, textvariable=self.dirHysplit, title="Hysplit directory")
        self.dirHysplitSelect.grid(row=2, column=0, columnspan=2, sticky=E+W, padx=5, pady=5)
        self.dirOutput=StringVar()
        self.dirOutput.set(param["dirOutput"])
        self.dirOutputSelect=SelectDirectory(self, textvariable=self.dirOutput, title="Output directory")
        self.dirOutputSelect.grid(row=3, column=0, columnspan=2, sticky=E+W, padx=5, pady=5)

        # ===== Station Frame                                ===================
        self.station_frame=LabelFrame(self,
                                      text="Station")
        self.station_frame.grid(row=4,
                                column=0,
                                sticky=E+W+S+N,
                                padx=5,
                                pady=5)
        # ===== Select station
        self.station=StringVar()
        self.station.set(param["station"])
        self.stationLabel=Label(self.station_frame, text="Station", justify=LEFT)
        self.stationLabel.grid(row=0, column=0, sticky=W, padx=5, pady=5)
        self.stationOptionMenu=OptionMenu(self.station_frame, self.station, param["station"], *locStation, command=self.station_callback)
        self.stationOptionMenu.grid(row=0, column=1, columnspan=3, sticky=W, padx=5, pady=5)
        # ===== Station coord.
        self.lon=StringVar()
        self.lon.set(locStation[self.station.get()][1])
        self.lonLabel=Label(self.station_frame, text="Longitude", justify=LEFT)
        self.lonLabel.grid(row=1, column=0, sticky=W, padx=5, pady=5)
        self.lonBackTrajEntry=EntryContext(self.station_frame, width=10, textvariable=self.lon)
        self.lonBackTrajEntry.grid(row=1, column=1, sticky=W, padx=5, pady=5)
        self.lat=StringVar()
        self.lat.set(locStation[self.station.get()][0])
        self.latLabel=Label(self.station_frame, text="Latitude", justify=LEFT)
        self.latLabel.grid(row=2, column=0, sticky=W, padx=5, pady=5)
        self.latBackTrajEntry=EntryContext(self.station_frame, width=10, textvariable=self.lat)
        self.latBackTrajEntry.grid(row=2, column=1, sticky=W, padx=5, pady=5)
        self.alt=StringVar()
        self.alt.set(param["alt"])
        self.altLabel=Label(self.station_frame, text="Altitude", justify=LEFT)
        self.altLabel.grid(row=1, column=4, sticky=W, padx=5, pady=5)
        self.altEntry=EntryContext(self.station_frame, width=10, textvariable=self.alt)
        self.altEntry.grid(row=1, column=5, sticky=W, padx=5, pady=5)
        
        # ===== Back Traj param =====
        self.bt_frame=LabelFrame(self,
                                text="Back-traj parameters")
        self.bt_frame.grid(row=5,
                            column=0,
                            sticky=E+W+S+N,
                            padx=5,
                            pady=5)
        # Time for BT
        self.hBT=StringVar()
        self.hBT.set(param["hBT"])
        self.hBTLabel=Label(self.bt_frame, text="Time for the back-trajectories [h]", justify=LEFT)
        self.hBTLabel.grid(row=0, column=0, sticky=W, padx=5, pady=5)
        self.hBTEntry=EntryContext(self.bt_frame, width=5, textvariable=self.hBT)
        self.hBTEntry.grid(row=0, column=1, sticky=W, padx=5, pady=5)
        # step between 2 BT
        self.stepHH=StringVar()
        self.stepHH.set(param["stepHH"])
        self.stepHHLabel=Label(self.bt_frame, text="Step between 2 end-points [h]", justify=LEFT)
        self.stepHHLabel.grid(row=2, column=0, sticky=W, padx=5, pady=5)
        self.stepHHEntry=EntryContext(self.bt_frame, width=5, textvariable=self.stepHH)
        self.stepHHEntry.grid(row=2, column=1, sticky=W, padx=5, pady=5)
        
        # ===== Time frame                          ===========================
        self.time_frame=LabelFrame(self,
                                  text="Date")
        self.time_frame.grid(row=4,
                             column=1,
                             sticky=E+W+S+N,
                             padx=5,
                             pady=5)

        # Start time
        self.startLabel=Label(self.time_frame, text="Starting day (YY/MM/DD/HH)", justify=LEFT)
        self.startLabel.grid(row=0,
                             column=0,
                             sticky=E+W+S+N,
                             padx=5, pady=5)
        self.buttonStart=Frame(self.time_frame)
        self.buttonStart.grid(row=1, column=0, sticky=W+E+S+N, padx=5, pady=5)
        self.YY=StringVar()
        self.YY.set(param["date"][0])
        self.YYLabel=Label(self.buttonStart, text="YY:", justify=LEFT).pack(side=LEFT)
        self.YYEntry=EntryContext(self.buttonStart, width=5, textvariable=self.YY).pack(side=LEFT)
        self.MM=StringVar()
        self.MM.set(param["date"][1])
        self.MMLabel=Label(self.buttonStart, text="MM:", justify=LEFT).pack(side=LEFT)
        self.MMEntry=EntryContext(self.buttonStart, width=5, textvariable=self.MM).pack(side=LEFT)
        self.DD=StringVar()
        self.DD.set(param["date"][2])
        self.DDLabel=Label(self.buttonStart, text="DD:", justify=LEFT).pack(side=LEFT)
        self.DDEntry=EntryContext(self.buttonStart, width=5, textvariable=self.DD).pack(side=LEFT)
        self.HH=StringVar()
        self.HH.set(param["date"][3])
        self.HHLabel=Label(self.buttonStart, text="HH:", justify=LEFT).pack(side=LEFT)
        self.HHEntry=EntryContext(self.buttonStart, width=5, textvariable=self.HH).pack(side=LEFT)
        # End time
        self.endLabel=Label(self.time_frame, text="Ending day (YY/MM/DD/HH)", justify=LEFT)
        self.endLabel.grid(row=2, column=0,
                           sticky=E+W,
                           padx=5, pady=0)
        self.buttonEnd=Frame(self.time_frame)
        self.buttonEnd.grid(row=3, column=0, sticky=W+E, padx=5, pady=5)
        self.YYend=StringVar()
        self.YYend.set(param["dateEnd"][0])
        self.YYendLabel=Label(self.buttonEnd, text="YY:", justify=LEFT).pack(side=LEFT)
        self.YYendEntry=EntryContext(self.buttonEnd, width=5, textvariable=self.YYend).pack(side=LEFT)
        self.MMend=StringVar()
        self.MMend.set(param["dateEnd"][1])
        self.MMendLabel=Label(self.buttonEnd, text="MM:", justify=LEFT).pack(side=LEFT)
        self.MMendEntry=EntryContext(self.buttonEnd, width=5, textvariable=self.MMend).pack(side=LEFT)
        self.DDend=StringVar()
        self.DDend.set(param["dateEnd"][2])
        self.DDendLabel=Label(self.buttonEnd, text="DD:", justify=LEFT).pack(side=LEFT)
        self.DDendEntry=EntryContext(self.buttonEnd, width=5, textvariable=self.DDend).pack(side=LEFT)
        self.HHend=StringVar()
        self.HHend.set(param["dateEnd"][3])
        self.HHendLabel=Label(self.buttonEnd, text="HH:", justify=LEFT).pack(side=LEFT)
        self.HHendEntry=EntryContext(self.buttonEnd, width=5, textvariable=self.HHend).pack(side=LEFT)

        # ===== CPU frame                          ===========================
        self.cpu_frame=LabelFrame(self,
                                  text="CPU")
        self.cpu_frame.grid(row=5,
                             column=1,
                             sticky=E+W+S+N,
                             padx=5,
                             pady=5)
        self.cpu=IntVar()
        self.cpu.set(cpu_count()-1)
        self.CPULabel=Label(self.cpu_frame, text="Number of CPU")
        self.CPULabel.grid(row=0, column=0, sticky=W, padx=5, pady=5)
        self.CPUEntry=EntryContext(self.cpu_frame, width=5, textvariable=self.cpu)
        self.CPUEntry.grid(row=0, column=1, sticky=W, padx=5, pady=5)
        self.l1=Label(self.cpu_frame, text="Each CPU is uses to its maximum. So be careful.")
        self.l1.grid(row=1, column=0, columnspan=5, sticky=W, padx=5, pady=5)

        self.columnconfigure(0,weight=10)
        self.columnconfigure(1,weight=10)
        self.rowconfigure(0,weight=10)
        self.rowconfigure(1,weight=10)
        self.rowconfigure(2,weight=10)
        self.rowconfigure(3,weight=10)
        self.rowconfigure(4,weight=10)
        self.rowconfigure(5,weight=10)
        # this allows using the mouse wheel even on the disabled Text widget
        # without the need to clic on said widget
        self.tk_focusFollowsMouse()

    def on_clear(self):
        self.text.configure(state=NORMAL)
        self.text.delete(1.0,END)
        self.text.configure(state=DISABLED)

    def on_save(self):
        with open('parameters'+os.sep+'localParamBackTraj_tmp.json', 'w') as fileSave:
            try:
                paramNew = {"dirGDAS": self.dirGDAS.get(),
                        "dirHysplit": self.dirHysplit.get(),
                        "dirOutput": self.dirOutput.get(),
                        "lat": self.lat.get(),
                        "lon": self.lon.get(),
                        "alt": self.alt.get(),
                        "station": self.station.get(),
                        "hBT": self.hBT.get(),
                        "cpu": self.cpu.get(),
                        "stepHH": self.stepHH.get(),
                        "date": [self.YY.get(), self.MM.get(), self.DD.get(), self.HH.get()],
                        "dateEnd": [self.YYend.get(), self.MMend.get(), self.DDend.get(), self.HHend.get()]}
            except (ValueError, SyntaxError):
                os.remove('parameters'+os.sep+'localParamBackTraj_tmp.json')
                showinfo("""Error""", """There is a problem somewhere... Probably a typo. The 'localParamBackTraj.json' file is not updated due to this problem.""")
                return 0

            json.dump(paramNew, fileSave, indent=4)
        shutil.copy('parameters'+os.sep+'localParamBackTraj_tmp.json', 'parameters'+os.sep+'localParamBackTraj.json')
        os.remove('parameters'+os.sep+'localParamBackTraj_tmp.json')
        # update the "param" dict.
        with open('parameters'+os.sep+'localParamBackTraj.json', 'r') as dataFile:
            param=json.load(dataFile)
        return 1
    
    def checkParam(self):
        with open('parameters'+os.sep+'localParamBackTraj.json', 'r') as dataFile:
            param=json.load(dataFile)
        dirOutput       = param["dirOutput"]
        HysplitExec     = param["dirHysplit"]+os.sep+"exec"+os.sep+"hyts_std"
        dirHysplit      = param["dirHysplit"]+os.sep+"working"+os.sep
        dirGDAS         = param["dirGDAS"]+os.sep
        CONTROL         = dirHysplit+"CONTROL"

        if not os.path.exists(dirGDAS):
            showerror("Error","The path for the GDAS file can not be found...")
            return (0, 0)
        if not os.path.exists(dirHysplit) or not os.path.exists(HysplitExec):
            showerror("Error","The Hysplit directory or the 'hyts_std' command do not exist...")
            return (0,0)
        if os.path.exists(dirOutput)==False:
            if sys.version_info.major >= 3:
                a=str(input("The output directory does not exist. Make one? ([y],n) "))
            else:
                a=str(raw_input("The output directory does not exist. Make one? ([y],n) "))
            if a=="y" or a=="Y" or a=="" or a=="yes":
                os.makedirs(dirOutput)
            else:
                showerror("Error","Script exit")
                return (0,0)
        return (1, param["cpu"])

    def on_run(self):
        # check
        errorCode = self.on_save()
        if errorCode==0:
            return
        errorCode, nbCPU  = self.checkParam()
        if errorCode==0:
            return
        
        # Compute the Back Traj
        for i in range(nbCPU):
            p = Process(target=BT)
            p.start()
        # block until the last process finish
        p.join()

        showinfo("""Done!""", """The back-trajectory script is finish. See the terminal output if error was raised.""")


    def station_callback(self, event):
        with open('parameters'+os.sep+'locationStation.json', 'r') as dataFile:
            locStation=json.load(dataFile)
        self.lat.set(locStation[self.station.get()][0])
        self.lon.set(locStation[self.station.get()][1])
        self.dirOutput.set(os.path.normpath(self.dirOutput.get()+os.sep+'..'+os.sep+self.station.get())+os.sep)
        self.exist_file()
        
    def exist_file(self):
        if not os.path.exists(self.dirOutput.get()):
            self.dirOutputSelect.dir_entry.config(foreground='red')
        else:
            self.dirOutputSelect.dir_entry.config(foreground='black')

    def on_about(self):
        showinfo("About BackTrajejectory tool's GUI","""This GUI is an adapted GUI from the game "The Battle For Westnoth", developed by Elvish_Hunter, 2014-2015, under the GNU GPL v2 license.

It uses hysplit to compute back trajectory for the given parameters.
The temperature, relative humidity and rain is keep in the back-traj files.

Once finish, all back-traj are converted in another format to be used with PSCF.

GUI tool : Samuel WEBER.

Icons are taken from the Tango Desktop Project (http://tango.freedesktop.org), and are released in the Public Domain""")

if __name__ == '__main__':
    root=Tk()

    ICONS={
               "about":PhotoImage(data=b'''
    R0lGODlhIAAgAOf/AExOK05QLVRRNFRWMlhZL1lYQF1eNFpcWWRhRF9jQ19hXmdnPWdoVWNndGdn
    cGVodmhpZ2ttamtsdXNwOmpufGhwd25wbWxwfm1xf3Rydm10fG9zgXB0gnd6QnJ2hHZ4dXt7T3t9
    P3Z9kXl9i3SAmHyBhIWGR4WEaoCEkomJXX+GmnuHoIWIeXmIp4iJdIaIhYSIl36Ko42Lj5CPYn+O
    oIuPnoWRno+QmZCSj4uTp22ZzHSXzHOax3Kb1YqZrHedypWbkXie36KgWp2clJyem36h1p6eqIKh
    3Z+hnoykz3+p0IWn3KSnhZemuaWmkKemi4yoy6qpe4qr1KansZapzpCsz42u16qsqZOt5Iyx05Ov
    07GxcJywyKevt7Gzd5Sx4pay1quvv5ez16+vuZqy3qizwa6ztZS42rK0saG12ra3jqW11Z624aC3
    1re0uZq615253by5hLW3tJy56ru6i7W5qZy82aO62ba3waC84Lq4vLi6t6W925+/3KXA16++0ru9
    ur6/qanB4K3B2sC+wq3B58PAxMDGlcDCvq3E477DxcLEwbLG37rHx8TGw67K4bXJ4sbMm7PK6brJ
    6sTI2MrIzMjKx8jJ08vKwbzL7LbO4L3M4LfP4cTN1cfOw8fNz7zP6b/P4svOytHSqMHR5MvQ0rzT
    5cnR2s/Rzs/Tw8PT59DWpM3S1dDSz77W6MzT6cbV6dLU0crW5dPW0sjX69LX2cnY7NXX1Mba5s/Y
    4MrZ7dbY1c3Z587a6Mvb7s/b6szc8Nnb19zfp9zdxtfc39Dd69rc2d7b4Nvhr9Le7Nne4dff6NDg
    9N3f3NTg7t7g3dXh7+Hg19zg8Nni6tzi5ODi39fj8drj6+LntePmwtzk7eHk4Nnl9ODk9OPl4uDm
    6OrouN7n7+Ln6uXn5OPo6+bo5eDp8efp5uHq8uXq7eXp+ejq5+jp8+Ps9Ofs7+rs6Ovxvu/s8evu
    6unu8Orv8uru/u3u+Ovw8+7w7PXzwu/w+vL4xfL3+fT5/Pz78v///yH5BAEKAP8ALAAAAAAgACAA
    AAj+AP8JHEiwoMGDCA+uI3SDw4MHHG4QWpewokA9FGJQKTQp06Q1OS7osXhwXg0RZOYs6bFDxw8r
    kkCpqDGP5EB8NVrMOVIEDiRSsEIxAmPFl48a+Gz+w0NiTpA8sGjZ4tWLly1ab6Qwo4HHprgLX4Ik
    ikq1V7JeumSZqiLGFwZxJN20wPIFFixcvpLp1Yv2jRZYTdyQRJHkiCRSsqgmcwYN2t5BbQS9QkGS
    ApkeoUzZMgttGrRr1qD9YuTnjjoKJBuw0fEIFq9fzqZpC6dN2zRYmkjba0DyQhoeZ2DpSgbNWjhz
    6MItk0WKE6N6F0jCgKJECiSzs5GHm7YsHC9SpKT+UbZIaAWfLHb6XYN9TbY2Vp9+yeJWxgxJfCO4
    JOoTjh8/cdQQI+A2pSwjTTceUETSMRj8AUoo9yxDjjvufHPMN8exM0IlSv1TywabwHINbenMEw89
    97RjzwiGdChQJTYkw4sy2qQTjzyz0GPPJVO4KNA3GEDDSye5uHPPLLHcY08YivgoEAqUJNMIEZ6k
    MkQ09+jjwTZOesjBKZ8AUUcgTwyTzhRGdCkQCxV0Ucs34pBTiwwZvKPmPx1sMUYJEjigwQcMIHDn
    PwaYkA042IxCRxwzDDCoExMwAc8+8AgDwgInDEqAEP7ksw84akQxAwGDDhCCF4cgs0okKSyQwKAm
    /7ggAAABBABAAZnC+g8OCuyxBwQv6DqQBQccEIGwBAGyB7J3BgQAOw=='''),
                "run":PhotoImage(data=b'''
    R0lGODlhIAAgAOeSAEZHQ0pLR0pMR1BRTVNUUFVWUldYVVhZVVtcV15gXWBhXGFhXmVlYmZmYmZn
    YmdpY2tsZ21va3BwbXBxbXBybHN0cHh4d3p8eX1/e35/en+BfH+BfYGBfoGBf4GDfIaIhoyNiJOU
    kpOVkpaXk5aXlJqamZqbmZyemqKioKqrqaysq66urLO0srS1tLa2tbe3tbi5trm6t7q6ucDBvsDB
    wMPDw8XFw8XFxcfHx8vLycvLys3Nzc/Pz8/QztHR0dLS0tLT0dPT09TU0tXV1dbW1tfX19fY1tra
    2tvb29zc3N3d3d/f3+Dg4OHh3+Li4uTk5OLl4OXl5ePm4eTm5Obm5ufn5+bo5ejo6Obp5efp5enp
    6efq5ujq5urq6unr5+rr6uvr6+ns6Ors6Ozs7Ort6evt6evt6uvt6+3t7evu6uzu6uzu6+3u7e7u
    7u3v6+3v7O7v7O7v7e/v7+3w7O7w7e7w7vDw8O/x7u/x7/Dx7/Hx8PHx8fDy7/Hy8PLy8vHz8PL0
    8fP08vT09PT18/T19PT29PX29PX29fb39fb39vf49vf49/j4+Pj5+Pn5+Pn6+fr7+v3+/f//////
    ////////////////////////////////////////////////////////////////////////////
    ////////////////////////////////////////////////////////////////////////////
    ////////////////////////////////////////////////////////////////////////////
    ////////////////////////////////////////////////////////////////////////////
    ////////////////////////////////////////////////////////////////////////////
    /////////////////////////////////////////////////////yH5BAEKAP8ALAAAAAAgACAA
    AAj+AP8JHEiwoMGDCBMqXMiwocOHECNKnKgQwwuKCgEw6FAD40EAkGgYCLHDI0EAg9KsOZFAhUmB
    KL14mWPlggQZJmPKFFMHyIIPNzDqlOmFzJ0YB0rwmAigEJkyZqKaKQPnDIkGLYZEBIDoDZ2vYL/2
    mTLBAg4kDwEs4tPnDx88b9SEwSIFSpweBEwccch1i8wwYsSE8cIlSxg9LgKseChgkRk3dO7k4ZPn
    zh1CRh6IQPtwQCM6fQIVQpQo0aMvGzgIkVjAUR5AhhZBiiQoRQUbFBF8Dq2IkY4ILDwqWFSGzqEm
    GVC8dIDoDpsRIJK8/AfhEQwPOaYLpKDBhfaBM74Kix9Pvrz58wUDAgA7'''),
                "save":PhotoImage(data=b'''
    R0lGODlhIAAgAOf8AAABACJKhSVOgydOiSJUjyxSjiNVkCZXkjBWjDFXjShZlFJUUSpalVRVU0lX
    aFVWVDVakFZYVTdck1dZVjlelVpcWTtgl1tdWkJfkTRjmS1kpjxhmD5imV1fXDBmqEFlnGBiX2Fj
    YEFomWJkYT1ppWNlYmRlYz1roURqm0VrnGZnZUFsqWdoZkdsnmhpZ0htnzpwrENuq0JvpTtxrWlr
    aEtwomttak1ypE5zpUt3rld2o014sF12nU55sVp4pVZ6rVh8r2B+q1t/smF/rFyAs3t9el2BtHx+
    e2GCqWiAqWOBrl6CtX1/fGSCsF+Dtn6AfWqCq2WDsWGFuICCf2CHtGKGuWOHumeIr12LvWSKt4SG
    g2uJt2WLuG6KrIaIhWuMtGeNunCMrmyNtWiOu2mPvHCOvGqQvXyPs2yTwG2UwY+RjniUtm+Ww3yU
    sZCSj3GYxXeYwJOVknmZwnqaw5WXlHubxHydxYWcuX2exn6fx3+gyIifvYChyZyem4ahxIGiyoqh
    v52fnIeixoOkzKGjoIqmyZKlvYunyqOlooyoy42pzKWnpKaopY+rzpCsz5Gt0KmrqKCsuZKu0pqt
    xpOv05evzautqpiwzqyuq5mxz6Gww62vrJuy0K6wrbCyrrGzr6y0vLK0sa21vaa2ybO1srS2s7W3
    tKm5zLa4tbe5tri6t628z7m7uLu9ur2/vLjAyLLB1bjD0bvDy8HDv7/ExsLEwcPFwsTGw8XHxLzI
    1sbIxcfJxr7K2MjKx8nLyMDM2srMycHN28vOysnO0MrP0c3Py87QzM/RzsrS29DSz9HT0NLU0dPV
    0tTW09XX1NbY1dLa4tXa3Nja1tbb3dnb19rc2dXd5tvd2tne4dze29zd593f3Nvg497g3d/h3tzi
    5ODi3+Hk4ODl6OPl4eTm4+Xn5Obo5efp5uXq7ejq5+nr6Ors6eft7+vu6u3v6+7w7e/x7u3y9fDy
    7/Hz8PL08fP18vT38/f59vn7+Pr8+fv9+vz/+////////////////yH5BAEKAP8ALAAAAAAgACAA
    AAj+AP8JHEiwoMGDCAkGO4Piw4s1vxJKJCjOh4Qgcgr5ycKhBraJCa1ZEPPoUKNHjzhx+oIAGUiD
    7F4AWqPjhpKTig49kgNB20uChmpsCBMLVhIJghT94dOIypCfAtG1IJCL4KgMjfLUmeNog8ufvJDE
    MgiFy583bAYpWQP11B5qRSZcmHvBgYhCacy8wSPgQoW/EbyoQxgM2pNN+fbp05cvnoJDZMCMUVTA
    Xj168+bFYYSQW7oO9VYFGD16gCIsVqo8Ij26yzYX7xCmonNv3CQKcv4MOqRIipMllS6pVJJiWjsm
    uBAW6bauW7g7G+ZgWWJEiJAeMEiU2QJhmLNwtbz+HKTGAp+3cebMXUFRR0iOGB40aFiS5oAsatKk
    nQPhzWCfVvCcN8443/hwwhgkyKfBDnUwoAk1EEozDiGLFNROCfAMOE443WQTTQoyoJEgDHxw0EZ+
    EEaoQmwDuaJGPdSY0w1+zTRDDAU/oLECHjXwYIwxyjDTzDbMjPPELARNIY051HDYDDNQGvNKAkoU
    AgQGtPQCjDDGSEONMtS0osVA27AAozTOdNONM8wYU8wuoBBwgwGi2IJLL8Lkx+Uy3YzQjUCImKJO
    NjQ2uY0zxviySyQBRHKnMc58WQyQ0mTTByEC2XBOJ1Mc4emnoIYq6hFTWLIMDQI9YM8TzWTj6qu9
    sMYqazbNPHFOAwItAM8R5jDi66/AmgNAesQWm94RxiyQ6zpHyAPJs9BGKw8A8lRr7bXyHKGKsv8s
    kM4R+nQi7rjk6gPAYuimu9gRqHC7wDngkitvJ+aqa+8RpLhrzhPz2Ovvv/rM88Qn7o4TSKejJizq
    FG5gwq0Jt3jTzTYRsrnMj8Ioqosts7jSCiuqmELKJ55sEocLApUSwgIst+zyyzC/DIIlAzWDiyqh
    bKLzzjz33DMpnqiSHFRECxQQADs='''),
                "exit":PhotoImage(data=b'''
    R0lGODlhIAAgAOfxAKQBAKMCBKUEAKUEBaYHBqcJB80AAKcKDs4ABM8ABKgMB9AAD6gMD6oOCKkP
    EKsRCdMHEckMFKUYFcERD68ZG7AaHLMdHrIeI7QfJMgdHNIcGrAmJLInJcohHdMeItQgIrQqLM4m
    JrcuLtEqL9UuLNcwLNkzNFZXVdM2MlZYVdo0NVdZVtU4NFhaV9U5OVlbWNY6OlpcWdc7O1tdWtg8
    PMtAPFxeW15gXds/Pto/Q19hXmBiX91BRWJkYctJRWNlYtlGRWVmZNtHRmZnZYdfXWdoZtxKTWhq
    Z2lraN5LTmpsac1ST2ttas5UVm1vbNxRUMpXVW5wbd5SUdBWV29xbt9TUcxZV3Byb99UWHFzcHN1
    ct1ZWXR2c95aWnV3dHZ4dXd5dnh6d3l7eHp8ed5iY3x+e31/fH6AfeJlZn+BfoCCf+RnZ4GDgIKE
    gYOFgoSGg4WHhIaIhYeJhoiKh+FzcomLiMl6eIqMiYuNioyOi42PjI6QjY+RjpCSj5GTkJ6Qi5KU
    kZOVkpSWk+iAgZWXlJaYlZeZlpial+aFg5qbmJudmZyem52fnJ6gnZ+hnueOjqCin6GjoOmQkMaa
    l6KkoaOloqSmo8Ken6WnpKaopaeppqiqp+uYlamrqM+in6utquidnqyuq+men62vrM2oqeyhobCy
    ru2iorGzr+qmpLO1stqsquGtrLe5tri6t7m7uLq8ubu9ury+u72/vO6ytL7BvcDCvsHDv9u9vMLE
    wcPFwsTGw8XHxN/Bv8bIxcjKx8nLyMrMycvOys3Py87QzM/RztDSz+vNy9LU0dPV0tTW09XX1NbY
    1dnb19rc2dvd2tze293f3N7g3eDi3+Hk4OPl4eTm4+vl5OXn5PLk5ezm5ebo5efp5vPm5ujq5/Tn
    5+nr6Ors6evu6u3v6+7w7e/x7vDy7/Hz8PL08fP18vT38/b49Pf59vj69/n7+Pr8+fv9+v//////
    /////////////////////////////////////////////////////yH5BAEKAP8ALAAAAAAgACAA
    AAj+AP8JHEiwoMGDBSGdWMiwYYoWOo5c8QIGDJconRAKPKEqj5szYLIwKdLjxgwdSJqhS8cSnTcv
    Gv+daLVHjpoxXqIgGdJjxxAw1Naxa9eOnbo4MU/IApTnTRoxXJzsDMKkzbZ27rK6Ywco6a5EfOq8
    MRNGSxQlSLLM4ebunduthpICc0RoT52PYbxQifJFD7i28N65a5coaTBKiwjpmePmqRctY/iEAyyY
    sMBrvQyeEFapUSJBdt+cGRPmDCBxlAcXviaigOZhmBwlItRn8ccybQiNS01YGwgoFTQTywRpUSFA
    eurAUZPmjaHd7wIP/rPBCq3gBU8Q0xSJkaFAe/D+5OnUSE8i6NK/SZgiKhUFBfAVbJBJbFPnz3zy
    3BmlChUm9PB8g0ETkqDBSSmnnFIKKALQ14klshHiR3JeuPGKK+h9c8ESg2DxxBZddLFFFZw0qF0n
    mERiHHJ3wJFILpVAl40FPtABBA9AGJFEEkYA8YiJxHSSCSWMJBIIH3gAAswmfpDjTjcV1ECGCibI
    QAMOMsCAAw2IANmJfZ4J0gcfubRyRiJOHqOACzR88IEGCyBggAEILLCGlw9CkkghfrwyixlvQOLk
    O6woMAIJcs6pqAFV4JniIoY08sodbORByaDvrKJACIjSicCnCDyBpyaUeHZkHXfwYUk5baEDjif+
    BXSAqAw45IAjEAE4+GUlEdaGRx+YcMMOO+Vs08wkA2RAAgsFCOCsAA7oiqKefO6hhyCb7FLNOuZs
    Aw0xRBAQAQoMCNfJuZl0Z4gggACSSCawMHNOOuFQs4walxAwQbnZBXmuJrwmIvBnmvBSjTnonAOO
    NG78Q0oBCph77iaYUFKJJYEEogoy1YhDzsficPOGQLjYIfG5nYwClinENEPNNjDDXA01ZiTl7yev
    VNIHKsEs00w00UgjtNDRNMNFUsOEEosphqjiyzDIJLPM1FRPrQwyTCA9Syaq1OLLL8GELczYZI8d
    DDA/JOVKK7DMYsstueSiy9x0152LLTbEpFAYCiu08EIMMcwg+OAz2EB4DJHEpPjiCAUEADs='''),
               "clear":PhotoImage(data=b'''
    R0lGODlhIAAgAOf/AHAFAHsGCJcAAHMKC3QLBHYMAKwAAYkLA3kRCbgAAIIQB8EAAHsUEbEGDIgX
    DIAaG5sYF4MkDYYmB80TDrIcFr8gHpE8A8EuLtIqKZVAGOMzM5lNEKBXA+BDQZdgEJVkEu5ISaBn
    D5xpDvZITZtpGJ9sHJxvJKRwIKBzKKV3Jat2HqV4NKZ5Lrd6EcB7CK5/NK2AQrKDOMKDEcWGIcKJ
    KrqKP7OLSr2PGLyPI7SNU7WPWsiPOMOSP8KSTb+VTsWUScOeCcWfAMChAMiiAMahIMWlAMOkEsuk
    AsenAb2mM8ifXb2gdMqpCNOgTceoJcmqG8GqN72pTc6sAMysDsysH8Smesaio8+mas2uLNOxAdWo
    WcyxI9WpYcmuU9C0BM6zGMyyL8WxVNOyJ9OvSNKyMceqqbmxl9m2D9G2Kda5ALa0mdO4H9KweNa6
    E9S9ANi7Fc2vrtu9AMm1ks65XNi8JdO+Jde9OtS8Ude9Q9rCCdjBHLm7uNq/PdjCKuHCENi/TdW/
    Wt3FENy8b8W/mOHIANXBacHAt9nFSdzGOeHIGNG/odnDZdzKF8DCvtHDhNzHQ83Cot/IMufIG+DJ
    KN6/ksfCweHBjdnGdc/GmeXMHt/NKt7KTcTGw97NNd3KVujOD+nLLeLMP97MXujPI+TFl8fJxuPO
    St3Lf+TGn+XPQ+jQMefQO+HRQ9HLtsrMyeXQVO7UHO3TKd7QdeLTTd7QkOLScfHWIOfWP+fTXuzY
    H/DWLdrNzs/Rzt/SmObVbebYYd/Rvt3Up+/bMejZW+fXduDVodPV0vbbNPLbT+7aZencZNXX1PXc
    SOvdXu7bbeHZq+ndbOnbgPneN+/fWfjiLvXhQtnb2OPctPjgVNvd2uPfvPrlPe7jePDhhvflT93f
    3Obd1vflV+7ilN7g3fvkYPvnSPXkg+7km+rhxuDi3ubh3/noYvLml+Hk4Ovkz+vj2/fojOPm4urm
    1+bo5f3udurp4P/uhenr6PrwjO3s4/Dr6f/wjevu6u3v7P31sv///yH5BAEKAP8ALAAAAAAgACAA
    AAj+AP8J1Jfjwwcd7wQqXMiwYcMlMVBR8mHinsOLGP+VoCTiA4sXcjKKXOiBDYp+JK6Q6DdyJAwl
    JUiEIHVCUUuRwD5Q4uGiyQ8WN0VWSWFphgwuHoAFxdhvRQ0tLnaosLEoCMulDMF94EGjxY0gj4q4
    w9pQ0QccQMSYY7eBgRWyC90BOZIMXw8EECgMUAf336kgdZqNieCgAwgMAeD0vRaESAYCDTSMuADA
    ApZnffMhELBgQgUFEgTtc7YF0FWsDwwkOFCghz965bxx4wOmHtkyAwBwgGePHjlv1GIp80RFHtld
    XUytK7cOmbdjuRLNqvUEHVlApsJtY4ZN1bFRmdLgzIpGRRvWS4imUdNVDVQsSZkmeTElbkuvpb3Q
    NINlK5a0M7G8QUgkUiByDh6A5HMTOlNAkwgsflCTSBvyBRKKFH2IQ10xLfVTxC95fBIHLNUUkcka
    XjDCyhRfiHNOEbS0dAcikeSRRxzCELgKE25oMgsfTJBRyE3BfIGLF4kw8ck0U+gRViDd+DLEHEs9
    8QofbtCRxS2pFMHKJkygYQQkWDmyBTFedFJEHsPYYYcnQ0BhCFxOPCJLKLgUQYwnQSRhRl//tDKE
    KH8c8oQQUagBqEKYPOFEGINUsuiklFYaVEAAOw=='''),
               "browse":PhotoImage(data=b'''
    R0lGODlhEAAQAMZ6AFpaWlxcXFxcXV1dXTNkpDRlpGBgYDZmpTdmo2FhYTdnpThopThopjlopDlo
    pWNjYztppjtqpjxqpWZmZmdnZ0BtqGpqamtra2xsbElxpW1tbUhzq29vb013r0d5tHNzc095rnZ2
    dlR9snp6emp/mWiAn35+fn9/f4CAgH+FjlmMw4aGhlyOxGCPw2iPvY+Um5WVlXuawJmZmZqampub
    m5ycnJ2dnZ6enp+fn6CgoKGhoX6n1H+o1KOjo4Gp1aSkpIKq1aWlpKWlpYSr1qampoar1IWs1qen
    p4au2Iiu2Kmpqaqqqqurq4uw2Yyw2aysrI2x2q2trY6z2q6urpK027CwsJG125K125O125K225O2
    25S23LKyspS33LOzs5W43Ju73re3t52937q6uqK/3729vcDAwMHBwMTExK7I5MXFxbHK5MfHx7PL
    5sjIyLTM5snJybXN5srKyrfO5rfO57fP57jP577T6cHV6sTX6/Dw8PDw8PDw8PDw8PDw8PDw8CH5
    BAEKAH8ALAAAAAAQABAAAAfOgH+Cg4SFf0QoiYkrhoMmcGxqaGhcMI1/I2pVUUxLSycaGBcXFox/
    IWdPS0dCP0pjam5yZhOCH2VKRD06OTg4OTo9PQmCHGG6OTY1NDM0NTc3A4IWXj0ZDtjZ2QgQIhRT
    OQtvdHR1c+foawQPSjcNd1lWV1n0WVpfbQcGQTUSeF0AA3aRgiSOggA6aFTIA6Zhwy1NkkCxwwAA
    jRcg0mCh4sQIjx0ggZCJMEBGCRdimgDxwbLlkCIdBJBw0IKFips4cXqIkaKAz59Af274EwgAOw=='''),
               "clear16":PhotoImage(data=b'''
    R0lGODlhEAAQAOeIAKsbDbg4HX9QCaxDFKxDJYRUCoJUEKhJGYpYDIlZDIZaGLtKKIdbGothIoxi
    IqZpCqlrCqttC7FsHbJyDLJ2C8htM7x6D5uHAKGIAcF9EJyLAKCQCKGRC6KRDaGSEKOSD6SSEKOT
    EaOTEqOTE6SUEaWUFKWWF6aWF6qOY6eXG6qZLqydIa2eKK2fKrChJLOjJ7CjNrynL72tMbqodrum
    h7mtULmuUbuwVsGyNryyW72yWsS0NMa1M8W1OMW2NdexYs29QcS7dcy+R9rCA9vDBM7ASNzEB9zF
    ENHCT9zGENzGFcnBgNXHVc7Brd/KJtjIT+PLEdDFltDDsOXNFNDJlufQGNzNWNPIuNLMm93PXuTS
    SeTTTOHTW+XUTu7XI+LUZ+bWVufXW9jUsOfYX/PbKu3aRtrVs+fZbdrWtOjabNvXtvbYYfbeL+zc
    aOrccuvdd+ved/vkN/PjZfzlPPvlRP3mPOPgzOTh0OTi0v3pUubk1v3qX/3qY/3rYf3rbPjqiPvq
    hP3sa+jn3P3sbfvti/3uff3vhP3vivDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw
    8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw
    8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw
    8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw
    8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw
    8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw
    8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8CH5BAEKAP8ALAAAAAAQABAA
    AAjBAK84YNDkn8GDCA0qeBBBgJSEEA1MyAChwb8gEA/SQGAhQwIVGjIeRFGAAgYZL9SINDjjAhA4
    Eg60WCIIIpYNT9pUAPDDjRAQOvQgpCIixoIAa/j4KfRHCIcbZhASGAAokKFBeejIeVPExYiDUXAc
    2tMnTx0yVZJo+VIC4QlCc+Kw8TKFyBAwPmwgZJGlTBUoRoYM2WKlQ0IxK9IcEawkDBMSaCDC6DHG
    SZczO0zYEZkCCRceH2qs/IfHQ4gcdxIGBAA7'''),
               "cut":PhotoImage(data=b'''
    R0lGODlhEAAQAMZ5AKYBAaYCAqcDA6YFBacFBagFBKYGBqgHB6gKCqkLC6sREbYPDqsUFK0ZGa4a
    Gq8bG6wcHK4dHcAZF60fH8AaGccaGckaGrAiIrAjI7AkJMwdHM0dHbAlJcofH8wgIM4gINAgINEg
    ILEpKc8hIdAhIdIhIdMiItAjI84kJMslJNQjI9UjI7MuLp42M9onJ7UxMbc3N7pBQaJJRLtERLtF
    Rb5YVs5qas5ubomJhMt4eIqMh4uNiMx7e42Pis1+fo+RjI+Rjc2AgJCSjpGTjs+GhpWXkpiZlpia
    lZqbl5qcl5udmZ6fm6Gjn6aopKeopKippamqpqmqp6qsp9ehodiioq2uqrCxrrGyr7Oyr7KzsLO0
    sbO1sLS1srW2srW2s7a4s7e5tLm6tr6/vMPEwcXGw8bIw8vLyuPFxczOyc3Oy9HSz9PT0tLU0NbW
    1djZ2Nvc2dvc2+Hh3+ri4ufo5u7v7vT19Pb29fb29vf39/Dw8PDw8PDw8PDw8PDw8PDw8PDw8CH5
    BAEKAH8ALAAAAAAQABAAAAe7gH+Ca0NMgoJaRYeLQndNY4dGak6LgjpsdFaCbVJlP5V/Q1t2SJA/
    aFVKoG47b3RRXF9pOmKgf0ddeEBLXmBQtn9wOnF1SU89cMB/V2FzUj1Zyn9mOGRYLcnAORMGMgEV
    GDygRAchGws1BRYgHQhTh1QEIzMUAH9yGhI0HgNEgiIqfPxBkUCQgBR/goAQIUjBhz83SrwQBGOF
    jT8kGAhi4eLEhghnBJ15YGLEBg6CqFxoACEkvBgOMoQMBAA7'''),
               "copy":PhotoImage(data=b'''
    R0lGODlhEAAQAKUeAIiKhYmLhoyOiZialZialpyemqGjn6mqp62uq6+wrbu8ury9ur2+u8PEw8fH
    xs/QzdDRz9TU1NnZ2dra2tvb2+Pj4uPk4uzs7O3t7e7u7e7u7u/v7u/v7/Dw7/Dw8PHx8PHx8fPz
    8/T09Pb29fb29vf39vf39/j49/r6+fr6+vv7+/z8+/7+/f////Dw8PDw8PDw8PDw8PDw8PDw8PDw
    8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8CH5BAEKAD8ALAAAAAAQABAAAAaKQIhi
    SCw+fsgfw8RsOhVJpYmzqVY5HBM0ueRQDoCweIzocgKttHoN6FIArY58Lm+1pxt0x8Hvd+xLGxNw
    dHSAJhoZen18dW0kGBKEhR0pIW0iGBeLjBolDW0fIB56dAKnAgAQC6wALHQpAyknFgBRAShzKbEp
    FQAFtyIlIysqEQS1W0kJAWNhBltBADs='''),
               "paste":PhotoImage(data=b'''
    R0lGODlhEAAQAMZZAGpDAmtEA2xEAXBJB3BKB3FKB3FKC3JLC3JNDnNNDnNOEHROEHRPEHVPEFxc
    W1xcXF5eXmZoZGdpZGpsaG5sZG5tZHBtY3BtZHFvZHNvZH5+e39/fKF8QKN8PYCAfbN7Iqd9O6R+
    Prl/I7p/I4WFhMCEJMKGKMWHJsWHJ8aIJ5WViZeXirqrkburkb6wmL+wmLGysrK0tLO1tbe3tLi5
    tbm5trm6tru7u8HCvszNys3Oy9jY1dnZ1tra2Nvb2eDg4Obk4Ofn5Ofn5ejo5unp5+rq6Ovq6Ovr
    6evr6uzs6uzs6+3t6+3t7O3u7e7u7e7u7u/v7e/v7u/v7/Dw7/Hx8fLy8v7+/f7+/v////Dw8PDw
    8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw
    8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8CH5
    BAEKAH8ALAAAAAAQABAAAAe6gH+Cf1IkD4cPJFKDgi0NAgEOKisrKg4BAgwvf0wHJSEXEBseHhoQ
    FBwiCU9ABSkYVD83szc/VRUoAEatKRFYU8DBWBImuq0nvlMyyzJRw8W7Bci/wVBLz8YE08oyMTBF
    2LvayVFMSEU+4UDjWE5KR0Q9OersSUVDOjY06gPTREI8amAZSMxYP19BduCYQRAFNCD9LDS5QjGK
    FQkoMupiYmAEiAwTQobsQPIDgid/WCwQwLKlSwUu/gQCADs='''),
               "select_all":PhotoImage(data=b'''
    R0lGODlhEAAQAKUZAAAAAIeJhIiKhYqMh4uNiIGXr4KYsLS1s7W2s7W2tKi+1qm/16rA2KvB2azC
    2q3D267E3K/F3bDG3rHH37LI4LPJ4evr6+zs7O7u7vDw8PLy8vT09PX19fb29vf39/j4+Pn5+fr6
    +vv7+/z8/P39/f7+/vDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw
    8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8CH5BAEKAD8ALAAAAAAQABAAAAaWwN9B
    QCwaiYjfL0AqlUik0UgkCoVAA6WApFgsGIyGWPwhaEuLgrrgWDvKWhJjXXjY7fDfdr5+QP4WeQIj
    DXQQahEXgiMODn4RERKSGIuOEJCSExMZgiJtdGoUGh5meiKPkgAUABUbpFohqBOrHB0dr3ogDwa8
    BqseHx64ArqXErMAHiDBpQEfz9AAH9LPWT8IR9kCCT9BADs=''')
               }


    ROOT_W,ROOT_H=800,480
    # the following string may be confusing, so here there's an explanation
    # Python supports two ways to perform string interpolation
    # the first one is the C-like style
    # the second one is the following, where each number enclosed in brackets points to an argument of the format method
    root.geometry("{0}x{1}+{2}+{3}".format(ROOT_W,
        ROOT_H,
        int((root.winfo_screenwidth()-ROOT_W)/2),
        int((root.winfo_screenheight()-ROOT_H)/2)))

    root.title("Back Traj calculator")
    root.rowconfigure(0,weight=1)
    root.columnconfigure(0,weight=1)
    # use a better style on Linux instead of the Motif-like one
    style=Style()
    if sys.platform.startswith("linux") and "clam" in style.theme_names():
        style.theme_use("clam")
    app=MainFrame(root)
    print("==== Welcome to the back-traj calculator ====")
    root.mainloop()
    sys.exit(0)
