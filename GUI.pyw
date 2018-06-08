#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import shutil
import numpy as np
from ast import literal_eval
import matplotlib.pyplot as plt
from multiprocessing import Process

from pyPSCF import pyPSCF
from pyPSCF.BackTrajHysplit import *

import time

if sys.version_info.major >= 3:
    from tkinter import *
    from tkinter.messagebox import *
    from tkinter.filedialog import *
    import tkinter.scrolledtext as tkst
    # ttk must be called last
    from tkinter.ttk import *
else:  # we are on Python 2
    # import Queue
    # tkinter modules
    from Tkinter import *
    from tkMessageBox import *
    from tkFileDialog import *
    import ScrolledText as tkst
    # ttk must be called last
    from ttk import *

# from modules.PSCF4GUI import PSCF, specie2study
# from modules.backTraj4GUI import BT


def arr2json(arr):
    return json.dumps(arr.tolist())


def json2arr(astr, dtype):
    return np.fromiter(json.loads(astr), dtype)


class TextRedirector(object):
    """Redirect the stdout to the window"""
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, str):
        self.widget.configure(state="normal")
        self.widget.insert("end", str, (self.tag,))
        self.widget.configure(state="disabled")


class ContextMenu(Menu):
    def __init__(self, x, y, widget):
        """A subclass of Menu, used to display a context menu in Text and
        Entry widgets.
        If the widget isn't active, some options do not appear"""
        if sys.version_info.major >= 3:
            super().__init__(None, tearoff=0) # otherwise Tk allows splitting it in a new window
        else:
            Menu.__init__(self, None, tearoff=0)
        self.widget = widget
        # MacOS uses a key called Command, instead of the usual Control used by Windows and Linux
        # so prepare the accelerator strings accordingly
        # For future reference, Mac also uses Option instead of Alt
        # also, a little known fact about Python is that it *does* support using the ternary operator
        # like in this case
        control_key = "Command" if self.tk.call('tk', 'windowingsystem') == "aqua" else "Ctrl"
        # str is necessary because in some instances a Tcl_Obj is returned instead of a string
        if str(widget.cget('state')) in (ACTIVE, NORMAL): # do not add if state is readonly or disabled
            self.add_command(label="Cut",
                             image=ICONS['cut'],
                             compound=LEFT,
                             accelerator='%s+X' % (control_key),
                             command=lambda: self.widget.event_generate("<<Cut>>"))
        self.add_command(label="Copy",
                         image=ICONS['copy'],
                         compound=LEFT,
                         accelerator='%s+C' % (control_key),
                         command=lambda: self.widget.event_generate("<<Copy>>"))
        if str(widget.cget('state')) in (ACTIVE, NORMAL):
            self.add_command(label="Paste",
                             image=ICONS['paste'],
                             compound=LEFT,
                             accelerator='%s+V' % (control_key),
                             command=lambda: self.widget.event_generate("<<Paste>>"))
        self.add_separator()
        self.add_command(label="Select all",
                         image=ICONS['select_all'],
                         compound=LEFT,
                         accelerator='%s+A' % (control_key),
                         command=self.on_select_all)
        self.tk_popup(x, y) # self.post does not destroy the menu when clicking out of it

    def on_select_all(self):
        # disabled Text widgets have a different way to handle selection
        if isinstance(self.widget, Text):
            # adding a SEL tag to a chunk of text causes it to be selected
            self.widget.tag_add(SEL, "1.0", END)
        elif isinstance(self.widget, Entry) or \
                isinstance(self.widget, Combobox):
            # apparently, the <<SelectAll>> event doesn't fire correctly if the widget is readonly
            self.widget.select_range(0, END)
        elif isinstance(self.widget, Spinbox):
            self.widget.selection("range", 0, END)


class EntryContext(Entry):
    def __init__(self, parent, **kwargs):
        """An enhanced Entry widget that has a right-click menu
        Use like any other Entry widget"""
        if sys.version_info.major >= 3:
            super().__init__(parent, **kwargs)
        else:
            Entry.__init__(self, parent, **kwargs)
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
        if windowingsystem == "win32":  # Windows, both 32 and 64 bit
            self.bind("<Button-3>", self.on_context_menu)
            self.bind("<KeyPress-App>", self.on_context_menu)
            self.bind("<Shift-KeyPress-F10>", self.on_context_menu)
            # for some weird reason, using a KeyPress binding to set the selection on
            # a readonly Entry or disabled Text doesn't work, but a KeyRelease does
            self.bind("<Control-KeyRelease-a>", self.on_select_all)
        elif windowingsystem == "aqua":  # MacOS with Aqua
            self.bind("<Button-2>", self.on_context_menu)
            self.bind("<Control-Button-1>", self.on_context_menu)
            self.bind("<Command-KeyRelease-a>", self.on_select_all)
        elif windowingsystem == "x11":  # Linux, FreeBSD, Darwin with X11
            self.bind("<Button-3>", self.on_context_menu)
            self.bind("<KeyPress-Menu>", self.on_context_menu)
            self.bind("<Shift-KeyPress-F10>", self.on_context_menu)
            self.bind("<Control-KeyRelease-a>", self.on_select_all)

    def on_context_menu(self, event):
        if str(self.cget('state')) != DISABLED:
            ContextMenu(event.x_root, event.y_root, event.widget)

    def on_select_all(self, event):
        self.select_range(0, END)


class SelectFile(LabelFrame):
    def __init__(self, parent, textvariable=None, title="Directory", **kwargs):
        """A subclass of LabelFrame sporting a readonly Entry and a Button with
        a folder icon.
        It comes complete with a context menu and a directory selection screen.
        """
        if sys.version_info.major >= 3:
            super().__init__(parent, text=title, **kwargs)
        else:
            LabelFrame.__init__(self, parent, text=title, **kwargs)
        self.textvariable = textvariable
        self.dir_entry = EntryContext(self,
                                      width=40,
                                      textvariable=self.textvariable)
        self.dir_entry.pack(side=LEFT,
                            fill=BOTH,
                            expand=YES)
        self.dir_button = Button(self,
                                 image=ICONS['browse'],
                                 compound=LEFT,
                                 text="Browse...",
                                 command=self.on_browse_file)
        self.dir_button.pack(side=LEFT)
        self.clear_button = Button(self,
                                   image=ICONS['clear16'],
                                   compound=LEFT,
                                   text="Clear",
                                   command=self.on_clear)
        self.clear_button.pack(side=LEFT)

    def on_browse_file(self):
        # if the user already selected a directory, try to use it
        current_dir = os.path.dirname(self.textvariable.get())
        if os.path.exists(current_dir):
            directory = askopenfilename(initialdir=current_dir)
        # otherwise attempt to detect the user's userdata folder
        else:
            # os.path.expanduser gets the current user's home directory on every platform
            if sys.platform == "win32":
                # get userdata directory on Windows
                # it assumes that you choose to store userdata in the My Games directory
                # while installing Wesnoth
                userdata = os.path.join(os.path.expanduser("~"),
                                        "Documents")
            elif sys.platform.startswith("linux"):  # we're on Linux; usually this string is 'linux2'
                userdata = os.path.join(os.path.expanduser("~"),
                                        "Documents")
            elif sys.platform == "darwin":  # we're on MacOS
                # bear in mind that I don't have a Mac, so this point may be bugged
                userdata = os.path.join(os.path.expanduser("~"),
                                        "Library")
            else:  # unknown system; if someone else wants to add other rules, be my guest
                userdata="."

            if os.path.exists(userdata):  # we may have gotten it wrong
                directory = askopenfilename(initialdir=userdata)
            else:
                directory = askopenfilename(initialdir=".")

        if directory:
            # use os.path.normpath, so on Windows the usual backwards slashes
            # are correctly shown
            self.textvariable.set(os.path.normpath(directory))

    def on_clear(self):
        self.textvariable.set("")


class SelectDirectory(LabelFrame):
    def __init__(self, parent, textvariable=None, title="Directory", **kwargs):
        """A subclass of LabelFrame sporting a readonly Entry and a Button with
        a folder icon.
        It comes complete with a context menu and a directory selection screen.
        """
        if sys.version_info.major >= 3:
            super().__init__(parent, text=title, **kwargs)
        else:
            LabelFrame.__init__(self, parent, text=title, **kwargs)

        self.textvariable = textvariable
        self.dir_entry = EntryContext(self,
                                      width=40,
                                      textvariable=self.textvariable)
        self.dir_entry.pack(side=LEFT,
                            fill=BOTH,
                            expand=YES)
        self.dir_button = Button(self,
                                 image=ICONS['browse'],
                                 compound=LEFT,
                                 text="Browse...",
                                 command=self.on_browse_dir)
        self.dir_button.pack(side=LEFT)
        self.clear_button = Button(self,
                                   image=ICONS['clear16'],
                                   compound=LEFT,
                                   text="Clear",
                                   command=self.on_clear)
        self.clear_button.pack(side=LEFT)

    def on_browse_dir(self):
        # if the user already selected a directory, try to use it
        current_dir = self.textvariable.get()
        if os.path.exists(current_dir):
            directory = askdirectory(initialdir=current_dir)
        # otherwise attempt to detect the user's userdata folder
        else:
            # os.path.expanduser gets the current user's home directory on every platform
            if sys.platform == "win32":
                # get userdata directory on Windows
                userdata = os.path.join(os.path.expanduser("~"),
                                        "Documents")
            elif sys.platform.startswith("linux"):  # we're on Linux;
                # usually this string is 'linux2'
                userdata = os.path.join(os.path.expanduser("~"),
                                        "Documents")
            elif sys.platform == "darwin":  # we're on MacOS
                # bear in mind that I don't have a Mac, so this point may be bugged
                userdata = os.path.join(os.path.expanduser("~"),
                                        "Library")
            else:  # unknown system;
                # if someone else wants to add other rules, be my guest
                userdata="."

            if os.path.exists(userdata): # we may have gotten it wrong
                directory = askdirectory(initialdir=userdata)
            else:
                directory = askdirectory(initialdir=".")

        if directory:
            # use os.path.normpath, so on Windows the usual backwards slashes
            # are correctly shown
            self.textvariable.set(os.path.normpath(directory)+os.sep)

        # app.exist_file()

    def on_clear(self):
        self.textvariable.set("")


class StationTab(Frame):
    def __init__(self, parent):
        if sys.version_info.major >= 3:
            super().__init__(parent)
        else:
            Frame.__init__(self, parent)

        self.station_frame = LabelFrame(self,
                                        text="Stations parameters")
        self.station_frame.grid(row=0,
                                column=0,
                                sticky=N+E+S+W)

        self.info = Label(self.station_frame,
                          text="Manage station longitude, latitude and altitude.")
        self.info.grid(row=0,
                       column=0,
                       sticky=N+E+S+W)
        # load station
        with open('parameters'+os.sep+'locationStation.json', 'r') as dataFile:
            self.locStation = json.load(dataFile)

        # ===== Station to modify or delete ==================================
        self.modif_frame = LabelFrame(self.station_frame,
                                      text="Modify existing station")
        self.modif_frame.grid(row=1,
                              column=0,
                              sticky=N+E+S+W)

        self.station = StringVar()
        # maybe the worth method to get the first key of this dict...
        for key in self.locStation:
            self.station.set(key)
            break
        self.lat = StringVar()
        self.lon = StringVar()
        self.alt = StringVar()
        self.lat.set(self.locStation[self.station.get()][0])
        self.lon.set(self.locStation[self.station.get()][1])
        self.alt.set(self.locStation[self.station.get()][2])

        self.stationLabel = Label(self.modif_frame, text="Station", justify=LEFT)
        self.stationLabel.grid(row=0, column=0, sticky=W, padx=5, pady=5)
        self.stationOptionMenu = OptionMenu(self.modif_frame, self.station, self.station.get(), *self.locStation, command=self.station_callback)
        self.stationOptionMenu.grid(row=0, column=1, columnspan=3, sticky=W, padx=5, pady=5)

        self.latLabel = Label(self.modif_frame, text="Latitude", justify=LEFT)
        self.latLabel.grid(row=1, column=0, sticky=E+W, padx=5, pady=5)
        self.latEntry = EntryContext(self.modif_frame, width=10, textvariable=self.lat)
        self.latEntry.grid(row=1, column=1, sticky=E+W, padx=5, pady=5)

        self.lonLabel = Label(self.modif_frame, text="Longitude", justify=LEFT)
        self.lonLabel.grid(row=2, column=0, sticky=E+W, padx=5, pady=5)
        self.lonEntry = EntryContext(self.modif_frame, width=10, textvariable=self.lon)
        self.lonEntry.grid(row=2, column=1, sticky=E+W, padx=5, pady=5)

        self.altLabel = Label(self.modif_frame, text="Altitude", justify=LEFT)
        self.altLabel.grid(row=3, column=0, sticky=E+W, padx=5, pady=5)
        self.altEntry = EntryContext(self.modif_frame, width=10, textvariable=self.alt)
        self.altEntry.grid(row=3, column=1, sticky=E+W, padx=5, pady=5)

        # ===== Button
        self.buttonBoxModif = Frame(self.modif_frame)
        self.buttonBoxModif.grid(row=4,
                                 column=0,
                                 columnspan=4,
                                 sticky=E+W)
        self.save_button = Button(self.buttonBoxModif,
                                  text="Save",
                                  image=ICONS['save'],
                                  compound=LEFT,
                                  width=15,  # to avoid changing size when callback is called
                                  command=self.on_save)
        self.save_button.pack(side=LEFT, padx=5, pady=5)
        self.delete_button = Button(self.buttonBoxModif,
                                    text="Delete",
                                    # image=ICONS['save'],
                                    compound=LEFT,
                                    width=15,  # to avoid changing size when callback is called
                                    command=self.on_delete)
        self.delete_button.pack(side=RIGHT, padx=5, pady=5)

        # ===== Add a station ===============================================
        self.add_frame = LabelFrame(self.station_frame,
                                    text="Add a new station")
        self.add_frame.grid(row=2,
                            column=0,
                            sticky=N+E+S+W,
                            padx=5,
                            pady=5)
        self.addLabelName = Label(self.add_frame, text="Station name")
        self.addLabelName.grid(row=0, column=0, sticky=E+W, padx=5, pady=5)
        self.addEntryName = EntryContext(self.add_frame, width=10)
        self.addEntryName.grid(row=0, column=1, sticky=E+W, padx=5, pady=5)
        self.addLabelLatitude = Label(self.add_frame, text="Latitude")
        self.addLabelLatitude.grid(row=1, column=0, sticky=E+W, padx=5, pady=5)
        self.addEntryLatitude = EntryContext(self.add_frame, width=10)
        self.addEntryLatitude.grid(row=1, column=1, sticky=E+W, padx=5, pady=5)
        self.addLabelLongitude = Label(self.add_frame, text="Longitude")
        self.addLabelLongitude.grid(row=2, column=0, sticky=E+W, padx=5, pady=5)
        self.addEntryLongitude = EntryContext(self.add_frame, width=10)
        self.addEntryLongitude.grid(row=2, column=1, sticky=E+W, padx=5, pady=5)
        self.addLabelAltitude = Label(self.add_frame, text="Altitude")
        self.addLabelAltitude.grid(row=3, column=0, sticky=E+W, padx=5, pady=5)
        self.addEntryAltitude = EntryContext(self.add_frame, width=10)
        self.addEntryAltitude.grid(row=3, column=1, sticky=E+W, padx=5, pady=5)

        # ===== Button
        self.buttonBoxAdd = Frame(self.add_frame)
        self.buttonBoxAdd.grid(row=4,
                               column=0,
                               columnspan=2,
                               sticky=E+W)
        self.save_button_add = Button(self.buttonBoxAdd,
                                      text="Save",
                                      image=ICONS['save'],
                                      compound=LEFT,
                                      width=15, # to avoid changing size when callback is called
                                      command=self.on_save_add)
        self.save_button_add.pack(side=LEFT, padx=5, pady=5)

    def station_callback(self, event):
        """Update the lat/lon/alt for the station"""
        self.lat.set(self.locStation[self.station.get()][0])
        self.lon.set(self.locStation[self.station.get()][1])
        self.alt.set(self.locStation[self.station.get()][2])

    def on_save(self):
        """Save the selected lon/lat/lat station from the 'locationStation.json' file"""
        with open('parameters'+os.sep+'locationStation_tmp.json', 'w') as fileSave:
            try:
                self.locStation[self.station.get()] = [self.lat.get(), self.lon.get(), self.alt.get()]
            except (ValueError, SyntaxError):
                os.remove('parameters'+os.sep+'locationStation_tmp.json')
                showinfo("""Error""", """There is a problem somewhere... \
                         Probably a typo. The 'locationStation.json' file is \
                         not updated due to this problem.""")
                return 0
            json.dump(self.locStation, fileSave, indent=4)
        shutil.copy('parameters'+os.sep+'locationStation_tmp.json', 'parameters'+os.sep+'locationStation.json')
        os.remove('parameters'+os.sep+'locationStation_tmp.json')
        print('Station '+self.station.get()+' saved')
        return 1

    def on_delete(self):
        """Delete the selected station from the 'locationStation.json' file"""
        with open('parameters'+os.sep+'locationStation_tmp.json', 'w') as fileSave:
            try:
                # remove the station from the dict
                rep = askokcancel(title="Beware!",
                                  message="You are about to delete the station "+self.station.get()+", are you sure of it?")
                if rep:
                    self.locStation.pop(self.station.get())
            except (ValueError, SyntaxError, KeyError):
                os.remove('parameters'+os.sep+'locationStation_tmp.json')
                showinfo("""Error""", """There is a problem somewhere...\
                         Probably a typo. The 'locationStation.json' file is \
                         not updated due to this problem.""")
                return 0
            json.dump(self.locStation, fileSave, indent=4)

        shutil.copy('parameters'+os.sep+'locationStation_tmp.json', 'parameters'+os.sep+'locationStation.json')
        os.remove('parameters'+os.sep+'locationStation_tmp.json')

        print('Station '+self.station.get()+' deleted')
        # TODO: change station and update the list
        for key in self.locStation:
            self.station.set(key)
            return
        self.station_callback()

        return 1

    def on_save_add(self):
        """Save the new station into the 'locationStation.json' file"""
        # check if the station already exist
        for key in self.locStation:
            if key == self.addEntryName.get():
                showinfo("""Error""", """The station already exist, try to \
                         update it instead of add it again.""")
                return 0
        with open('parameters'+os.sep+'locationStation_tmp.json', 'w') as fileSave:
            try:
                # check if the coordinate are float
                float(self.addEntryLatitude.get())
                float(self.addEntryLongitude.get())
                float(self.addEntryAltitude.get())
            except (ValueError, SyntaxError):
                os.remove('parameters'+os.sep+'locationStation_tmp.json')
                showinfo("""Error""", """There is a problem somewhere... \
                         Probably a typo. The 'locationStation.json' file is \
                         not updated due to this problem.""")
                return 0

            self.locStation[self.addEntryName.get()] = [self.addEntryLatitude.get(), self.addEntryLongitude.get(), self.addEntryAltitude.get()]
            json.dump(self.locStation, fileSave, indent=4)
        shutil.copy('parameters'+os.sep+'locationStation_tmp.json', 'parameters'+os.sep+'locationStation.json')
        os.remove('parameters'+os.sep+'locationStation_tmp.json')
        print('Station '+self.addEntryName.get()+' added')
        # TODO
        # add a callback so when a station is add, we can see it in the list
        return 1

# class TextoutputTab(Frame):
#    def __init__(self, parent):
#        if sys.version_info.major>=3:
#            super().__init__(parent)
#        else:
#            Frame.__init__(self, parent)
#
#        self.output_frame = LabelFrame(self,
#                                    text="Output")
#        self.output_frame.grid(row=0,
#                              column=0,
#                              sticky=N+E+S+W)
#        # ==== Text widget for output ========================================
#        self.output_text = tkst.ScrolledText(self.output_frame,
#                                           wrap="word",
#                                           width=200,
#                                           height=30)
#        self.output_text.grid(row=0,
#                             column=0,
#                             sticky=N+E+S+W)
#        self.output_text.tag_configure("stderr", foreground="#b22222")


class BacktrajTab(Frame):
    def __init__(self, parent):
        if sys.version_info.major >= 3:
            super().__init__(parent)
        else:
            Frame.__init__(self, parent)

        # Import local Param from the JSON file
        with open('parameters'+os.sep+'localParamBackTraj.json', 'r') as dataFile:
            self.param = json.load(dataFile)
        with open('parameters'+os.sep+'locationStation.json', 'r') as dataFile:
            self.locStation = json.load(dataFile)

        self.Backtraj_frame = LabelFrame(self,
                                         text="Back-Trajectory options")
        self.Backtraj_frame.grid(row=0,
                                 column=0,
                                 sticky=N+E+S+W)
        # Directory
        self.dirGDAS = StringVar()
        self.dirGDAS.set(self.param["dirGDAS"])
        self.dirGDASSelect = SelectDirectory(self.Backtraj_frame, textvariable=self.dirGDAS, title="Meteo (GDAS) directory")
        self.dirGDASSelect.grid(row=0, column=0, columnspan=2, sticky=E+W, padx=5, pady=5)
        self.dirHysplit = StringVar()
        self.dirHysplit.set(self.param["dirHysplit"])
        self.dirHysplitSelect = SelectDirectory(self.Backtraj_frame, textvariable=self.dirHysplit, title="Hysplit directory")
        self.dirHysplitSelect.grid(row=1, column=0, columnspan=2, sticky=E+W, padx=5, pady=5)
        self.dirOutput = StringVar()
        self.dirOutput.set(self.param["dirOutput"])
        self.dirOutputSelect = SelectDirectory(self.Backtraj_frame, textvariable=self.dirOutput, title="Output directory")
        self.dirOutputSelect.grid(row=2, column=0, columnspan=2, sticky=E+W, padx=5, pady=5)

        # ===== Station Frame                                ===================
        self.station_frame = LabelFrame(self.Backtraj_frame,
                                        text="Station")
        self.station_frame.grid(row=3,
                                column=0,
                                sticky=E+W+S+N,
                                padx=5,
                                pady=5)
        # ===== Select station
        self.station = StringVar()
        self.station.set(self.param["station"])
        self.stationLabel = Label(self.station_frame, text="Station", justify=LEFT)
        self.stationLabel.grid(row=0, column=0, sticky=W, padx=5, pady=5)
        self.stationOptionMenu = OptionMenu(self.station_frame, self.station, self.param["station"], *self.locStation, command=self.station_callback)
        self.stationOptionMenu.grid(row=0, column=1, columnspan=3, sticky=W, padx=5, pady=5)
        # ===== Station coord.
        self.lon = StringVar()
        self.lon.set(self.locStation[self.station.get()][1])
        self.lonLabel = Label(self.station_frame, text="Longitude", justify=LEFT)
        self.lonLabel.grid(row=1, column=0, sticky=W, padx=5, pady=5)
        self.lonBackTrajEntry = EntryContext(self.station_frame, width=10, textvariable=self.lon)
        self.lonBackTrajEntry.grid(row=1, column=1, sticky=W, padx=5, pady=5)
        self.lat = StringVar()
        self.lat.set(self.locStation[self.station.get()][0])
        self.latLabel = Label(self.station_frame, text="Latitude", justify=LEFT)
        self.latLabel.grid(row=2, column=0, sticky=W, padx=5, pady=5)
        self.latBackTrajEntry = EntryContext(self.station_frame, width=10, textvariable=self.lat)
        self.latBackTrajEntry.grid(row=2, column=1, sticky=W, padx=5, pady=5)
        self.alt = StringVar()
        self.alt.set(self.locStation[self.station.get()][2])
        self.altLabel = Label(self.station_frame, text="Altitude", justify=LEFT)
        self.altLabel.grid(row=1, column=4, sticky=W, padx=5, pady=5)
        self.altEntry = EntryContext(self.station_frame, width=10, textvariable=self.alt)
        self.altEntry.grid(row=1, column=5, sticky=W, padx=5, pady=5)

        # ===== Time frame                          ===========================
        self.time_frame = LabelFrame(self.Backtraj_frame,
                                     text="Date")
        self.time_frame.grid(row=3,
                             column=1,
                             sticky=E+W+S+N,
                             padx=5,
                             pady=5)

        # Start time
        self.startLabel = Label(self.time_frame, text="Starting day (YYYY-MM-DD HH)", justify=LEFT)
        self.startLabel.grid(row=0,
                             column=0,
                             sticky=E+W+S+N,
                             padx=5, pady=5)
        self.buttonMin = Frame(self.time_frame)
        self.buttonMin.grid(row=0, column=1, sticky=W+E+S+N, padx=5, pady=5)
        self.dateMin = StringVar()
        self.dateMin.set(self.param["dateMin"])
        self.dateMinEntry = EntryContext(self.buttonMin, width=20,
                                         textvariable=self.dateMin).pack(side=LEFT)
        # End date
        self.endLabel = Label(self.time_frame, text="Ending day (YYYY-MM-DD HH)", justify=LEFT)
        self.endLabel.grid(row=1, column=0,
                           sticky=E+W+S+N,
                           padx=5, pady=0)
        self.buttonMax = Frame(self.time_frame)
        self.buttonMax.grid(row=1, column=1, sticky=W+E+S+N, padx=5, pady=5)
        self.dateMax = StringVar()
        self.dateMax.set(self.param["dateMax"])
        self.dateMaxEntry = EntryContext(self.buttonMax, width=20,
                                         textvariable=self.dateMax).pack(side=LEFT)

        #
        # self.YY = StringVar()
        # self.YY.set(self.param["date"][0])
        # self.YYLabel = Label(self.buttonStart, text="YY:", justify=LEFT).pack(side=LEFT)
        # self.YYEntry = EntryContext(self.buttonStart, width=5, textvariable=self.YY).pack(side=LEFT)
        # self.MM = StringVar()
        # self.MM.set(self.param["date"][1])
        # self.MMLabel = Label(self.buttonStart, text="MM:", justify=LEFT).pack(side=LEFT)
        # self.MMEntry = EntryContext(self.buttonStart, width=5, textvariable=self.MM).pack(side=LEFT)
        # self.DD = StringVar()
        # self.DD.set(self.param["date"][2])
        # self.DDLabel = Label(self.buttonStart, text="DD:", justify=LEFT).pack(side=LEFT)
        # self.DDEntry = EntryContext(self.buttonStart, width=5, textvariable=self.DD).pack(side=LEFT)
        # self.HH = StringVar()
        # self.HH.set(self.param["date"][3])
        # self.HHLabel = Label(self.buttonStart, text="HH:", justify=LEFT).pack(side=LEFT)
        # self.HHEntry = EntryContext(self.buttonStart, width=5, textvariable=self.HH).pack(side=LEFT)
        # # End time
        # self.endLabel = Label(self.time_frame, text="Ending day (YY/MM/DD/HH)", justify=LEFT)
        # self.endLabel.grid(row=2, column=0,
        #                    sticky=E+W,
        #                    padx=5, pady=0)
        # self.buttonEnd = Frame(self.time_frame)
        # self.buttonEnd.grid(row=3, column=0, sticky=W+E, padx=5, pady=5)
        # self.YYend = StringVar()
        # self.YYend.set(self.param["dateEnd"][0])
        # self.YYendLabel = Label(self.buttonEnd, text="YY:", justify=LEFT).pack(side=LEFT)
        # self.YYendEntry = EntryContext(self.buttonEnd, width=5, textvariable=self.YYend).pack(side=LEFT)
        # self.MMend = StringVar()
        # self.MMend.set(self.param["dateEnd"][1])
        # self.MMendLabel = Label(self.buttonEnd, text="MM:", justify=LEFT).pack(side=LEFT)
        # self.MMendEntry = EntryContext(self.buttonEnd, width=5, textvariable=self.MMend).pack(side=LEFT)
        # self.DDend = StringVar()
        # self.DDend.set(self.param["dateEnd"][2])
        # self.DDendLabel = Label(self.buttonEnd, text="DD:", justify=LEFT).pack(side=LEFT)
        # self.DDendEntry = EntryContext(self.buttonEnd, width=5, textvariable=self.DDend).pack(side=LEFT)
        # self.HHend = StringVar()
        # self.HHend.set(self.param["dateEnd"][3])
        # self.HHendLabel = Label(self.buttonEnd, text="HH:", justify=LEFT).pack(side=LEFT)
        # self.HHendEntry = EntryContext(self.buttonEnd, width=5, textvariable=self.HHend).pack(side=LEFT)

        # ===== Back Traj param     ===========================================
        self.bt_frame = LabelFrame(self.Backtraj_frame,
                                   text="Back-traj parameters")
        self.bt_frame.grid(row=4,
                           column=0,
                           sticky=E+W+S+N,
                           padx=5,
                           pady=5)
        # Time for BT
        self.hBT = StringVar()
        self.hBT.set(self.param["hBT"])
        self.hBTLabel = Label(self.bt_frame, text="Time for the back-trajectories [h]", justify=LEFT)
        self.hBTLabel.grid(row=0, column=0, sticky=W, padx=5, pady=5)
        self.hBTEntry = EntryContext(self.bt_frame, width=5, textvariable=self.hBT)
        self.hBTEntry.grid(row=0, column=1, sticky=W, padx=5, pady=5)
        # step between 2 BT
        self.stepHH = StringVar()
        self.stepHH.set(self.param["stepHH"])
        self.stepHHLabel = Label(self.bt_frame, text="Step between 2 starting back-trajectories. [h]", justify=LEFT)
        self.stepHHLabel.grid(row=2, column=0, sticky=W, padx=5, pady=5)
        self.stepHHEntry = EntryContext(self.bt_frame, width=5, textvariable=self.stepHH)
        self.stepHHEntry.grid(row=2, column=1, sticky=W, padx=5, pady=5)

        # ===== CPU frame                          ===========================
        self.cpu_frame = LabelFrame(self.Backtraj_frame,
                                    text="CPU")
        self.cpu_frame.grid(row=4,
                            column=1,
                            sticky=E+W+S+N,
                            padx=5,
                            pady=5)
        self.cpu = IntVar()
        self.cpu.set(1) # os.cpu_count()-1)
        self.CPULabel = Label(self.cpu_frame, text="Number of CPU")
        self.CPULabel.grid(row=0, column=0, sticky=W, padx=5, pady=5)
        self.CPUEntry = EntryContext(self.cpu_frame, width=5, textvariable=self.cpu)
        self.CPUEntry.grid(row=0, column=1, sticky=W, padx=5, pady=5)
        self.l1 = Label(self.cpu_frame, text="Each CPU is uses to its maximum. So be careful.")
        self.l1.grid(row=1, column=0, columnspan=5, sticky=W, padx=5, pady=5)

        # ====================================================================
        self.columnconfigure(0, weight=10)
        self.Backtraj_frame.columnconfigure(0, weight=10)
        self.Backtraj_frame.columnconfigure(1, weight=10)
        self.rowconfigure(0, weight=10)
        self.Backtraj_frame.rowconfigure(0, weight=1)
        self.Backtraj_frame.rowconfigure(1, weight=1)
        self.Backtraj_frame.rowconfigure(2, weight=1)
        self.Backtraj_frame.rowconfigure(3, weight=10)
        self.Backtraj_frame.rowconfigure(4, weight=10)

        self.exist_file()

    def on_clear(self):
        self.text.configure(state=NORMAL)
        self.text.delete(1.0, END)
        self.text.configure(state=DISABLED)

    def checkParam(self):
        dirOutput = self.param["dirOutput"]+os.sep
        HysplitExec = self.param["dirHysplit"]+os.sep+"exec"+os.sep+"hyts_std"
        if sys.platform == "win32":
            HysplitExec += ".exe"
        dirHysplit = self.param["dirHysplit"]+os.sep+"working"+os.sep
        dirGDAS = self.param["dirGDAS"]+os.sep
        CONTROL = dirHysplit+"CONTROL"

        if not os.path.exists(dirGDAS):
            showerror("Error", "The path for the GDAS file can not be found...")
            return (0, 0)
        if not os.path.exists(dirHysplit):
            showerror("Error", "The Hysplit directory command do not exist...")
            return (0, 0)
        if not os.path.exists(HysplitExec):
            showerror("Error", "The Hysplit 'hyts_std' command do not exist...")
            return (0, 0)
        if os.path.exists(dirOutput) == False:
            if sys.version_info.major >= 3:
                a = str(input("The output directory does not exist. Make one? ([y], n) "))
            else:
                a = str(raw_input("The output directory does not exist. Make one? ([y], n) "))
            if a == "y" or a == "Y" or a == "" or a == "yes":
                os.makedirs(dirOutput)
            else:
                showerror("Error", "Script exit")
                return (0, 0)
        return (1, self.param["cpu"])

    def on_save(self):
        with open('parameters'+os.sep+'localParamBackTraj_tmp.json', 'w') as fileSave:
            try:
                paramNew = {
                    "dirGDAS": self.dirGDAS.get(),
                    "dirHysplit": self.dirHysplit.get(),
                    "dirOutput": self.dirOutput.get(),
                    "lat": self.lat.get(),
                    "lon": self.lon.get(),
                    "alt": self.alt.get(),
                    "station": self.station.get(),
                    "hBT": self.hBT.get(),
                    "cpu": self.cpu.get(),
                    "stepHH": self.stepHH.get(),
                    "dateMin": self.dateMin.get(),
                    "dateMax": self.dateMax.get(),
                }
            except (ValueError, SyntaxError):
                os.remove('parameters'+os.sep+'localParamBackTraj_tmp.json')
                showinfo("""Error""", """There is a problem somewhere... Probably a typo. The 'localParamBackTraj.json' file is not updated due to this problem.""")
                return 0

            json.dump(paramNew, fileSave, indent=4)
        shutil.copy('parameters'+os.sep+'localParamBackTraj_tmp.json', 'parameters'+os.sep+'localParamBackTraj.json')
        os.remove('parameters'+os.sep+'localParamBackTraj_tmp.json')
        # update the "param" dict.
        self.param = paramNew
        return 1

    def station_callback(self, event):
        self.lat.set(self.locStation[self.station.get()][0])
        self.lon.set(self.locStation[self.station.get()][1])
        self.dirOutput.set(os.path.normpath(self.dirOutput.get()+os.sep+'..'+os.sep+self.station.get())+os.sep)
        self.exist_file()

    def exist_file(self):
        if not os.path.exists(self.dirOutput.get()):
            self.dirOutputSelect.dir_entry.config(foreground='red')
        else:
            self.dirOutputSelect.dir_entry.config(foreground='black')


class PSCFTab(Frame):
    def __init__(self, parent):
        if sys.version_info.major >= 3:
            super().__init__(parent)
        else:
            Frame.__init__(self, parent)

        # Import local Param from the JSON file
        with open('parameters'+os.sep+'localParamPSCF.json', 'r') as dataFile:
            self.param = json.load(dataFile)

        with open('parameters'+os.sep+'locationStation.json', 'r') as dataFile:
            self.locStation = json.load(dataFile)

        self.PSCF_frame = LabelFrame(self,
                                     text="PSCF options")
        self.PSCF_frame.grid(row=0,
                             column=0,
                             sticky=N+E+S+W)

        # ===== Directory and concentration file ===============================
        self.dirBackTraj = StringVar()
        self.dirBackTraj.set(self.param["dirBackTraj"])
        self.dirBackTrajSelect = SelectDirectory(self.PSCF_frame, textvariable=self.dirBackTraj, title="Back-trajectory directory")
        self.dirBackTrajSelect.grid(row=0, columnspan=3, sticky=E+W, padx=5)

        self.Cfile = StringVar()
        self.Cfile.set(self.param["Cfile"])
        self.CfileSelect = SelectFile(self.PSCF_frame, textvariable=self.Cfile, title="Concentration file")
        self.CfileSelect.grid(row=1, columnspan=3, sticky=E+W, padx=5)

        # ============ Station Frame ===========================================
        self.station_frame = LabelFrame(self.PSCF_frame,
                                        text="Station")
        self.station_frame.grid(row=2,
                                column=0,
                                sticky=E+W+S+N,
                                padx=5,
                                pady=5)
        # Station name
        self.station = StringVar()
        self.station.set(self.param["station"])
        self.stationLabel = Label(self.station_frame, text="Station", justify=LEFT)
        self.stationLabel.grid(row=0, column=0, columnspan=2, sticky=W, padx=5, pady=5)
        self.stationOptionMenu = OptionMenu(self.station_frame, self.station,
                                            self.param["station"], *self.locStation, command=self.station_callback)
        self.stationOptionMenu.grid(row=0, column=2, sticky=W, padx=5, pady=5)
        self.stationOptionMenu.configure(width=6)
        # Prefix for the back-trajectory
        self.prefixTraj = StringVar()
        self.prefixTraj.set(self.param["prefix"])
        self.prefixTrajLabel = Label(self.station_frame, text="Back-traj prefix", justify=LEFT)
        self.prefixTrajLabel.grid(row=1, column=0, columnspan=2, sticky=W, padx=5, pady=5)
        self.prefixTrajEntry = EntryContext(self.station_frame, width=10, textvariable=self.prefixTraj)
        self.prefixTrajEntry.grid(row=1, column=2, sticky=W, padx=5, pady=5)
        # Ref point
        self.lon0 = StringVar()
        self.lon0.set(self.locStation[self.param["station"]][1])
        self.lon0Label = Label(self.station_frame, text="Lon", justify=LEFT)
        self.lon0Label.grid(row=2, column=0, sticky=W, padx=5, pady=5)
        self.lon0Entry = EntryContext(self.station_frame, width=5, textvariable=self.lon0)
        self.lon0Entry.grid(row=2, column=1, sticky=W, padx=5, pady=5)
        self.lat0 = StringVar()
        self.lat0.set(self.locStation[self.param["station"]][0])
        self.lat0Label = Label(self.station_frame, text="Lat", justify=LEFT)
        self.lat0Label.grid(row=3, column=0, sticky=W, padx=5, pady=5)
        self.lat0Entry = EntryContext(self.station_frame, width=5, textvariable=self.lat0)
        self.lat0Entry.grid(row=3, column=1, sticky=W, padx=5, pady=5)

        # ============== Back Traj Frame ========================
        self.Backtraj_frame = LabelFrame(self.PSCF_frame,
                                         text="Back Trajectory")
        self.Backtraj_frame.grid(row=2,
                                 column=1,
                                 sticky=E+W+S+N,
                                 padx=5,
                                 pady=5)
        # Back traj
        self.backTraj = IntVar()
        self.backTraj.set(self.param["backTraj"])
        self.backTrajLabel = Label(self.Backtraj_frame, text="Back-trajectory [h]", justify=LEFT)
        self.backTrajLabel.grid(row=0, column=0, sticky=W, padx=5, pady=5)
        self.backTrajEntry = EntryContext(self.Backtraj_frame, width=5, textvariable=self.backTraj)
        self.backTrajEntry.grid(row=0, column=1, sticky=W, padx=5, pady=5)
        # Add hour
        self.add_hour = StringVar()
        self.add_hour.set(self.param["add_hour"])
        self.add_hourLabel = Label(self.Backtraj_frame, text="Add hour", justify=LEFT)
        self.add_hourLabel.grid(row=2, column=0, sticky=W, padx=5, pady=5)
        self.add_hourEntry = EntryContext(self.Backtraj_frame, width=28, textvariable=self.add_hour, justify=LEFT)
        self.add_hourEntry.grid(row=3, column=0, columnspan=2, sticky=W, padx=5, pady=5)
        # Cut with rain
        self.cutWithRain = BooleanVar()
        self.cutWithRain.set(self.param["cutWithRain"])
        self.cutWithRainCheck = Checkbutton(self.Backtraj_frame, text="Cut when it's raining", variable=self.cutWithRain)
        self.cutWithRainCheck.grid(row=4, column=0, sticky=W, padx=5, pady=5)

        # ============== Weighting Function Frame ========================
        self.wf_frame = LabelFrame(self.PSCF_frame,
                                   text="Weighting function")
        self.wf_frame.grid(row=2,
                           column=2,
                           sticky=E+W+S+N,
                           padx=5,
                           pady=5)
        # Weighting function
        self.weigthingFunction = BooleanVar()
        self.weigthingFunction.set(self.param["wF"])
        self.weigthingFunctionCheck = Checkbutton(self.wf_frame, text="Use the weighting function", variable=self.weigthingFunction, command=self.wf_callback)
        self.weigthingFunctionCheck.grid(row=0, column=0, sticky=W, padx=5, pady=5)

        self.wf_manual = BooleanVar()
        self.wf_manual.set(self.param["wFmanual"])
        manualChoice = ("Auto", "User defined")[self.wf_manual.get()]
        self.varChoiceManual = StringVar(self.wf_frame)
        self.varChoiceManual.set(manualChoice)
        self.wf_manualChoice = OptionMenu(self.wf_frame, self.varChoiceManual, manualChoice, "User defined", "Auto", command=self.wf_manual_callback)
        self.wf_manualChoice.grid(row=0, column=1, sticky=W, padx=5, pady=5)


        self.wf_frame_manual_choice = Frame(self.wf_frame)
        self.wf_frame_manual_choice.grid(row=1, column=0, columnspan=2, sticky=W, padx=5, pady=5)
        self.wFbox0 = Frame(self.wf_frame_manual_choice)
        self.wFbox0.grid(row=1, column=0, padx=5, sticky=E)
        self.wFbox1 = Frame(self.wf_frame_manual_choice)
        self.wFbox1.grid(row=2, column=0, padx=5, sticky=E)
        self.wFbox2 = Frame(self.wf_frame_manual_choice)
        self.wFbox2.grid(row=3, column=0, padx=5, sticky=E)
        self.wFbox3 = Frame(self.wf_frame_manual_choice)
        self.wFbox3.grid(row=4, column=0, padx=5, sticky=E)
        self.wFlim0 = StringVar()
        self.wFlim0.set(self.param["wFlim"][0])
        self.wFlim1 = StringVar()
        self.wFlim1.set(self.param["wFlim"][1])
        self.wFlim2 = StringVar()
        self.wFlim2.set(self.param["wFlim"][2])
        self.wFval0 = StringVar()
        self.wFval0.set(self.param["wFval"][0])
        self.wFval1 = StringVar()
        self.wFval1.set(self.param["wFval"][1])
        self.wFval2 = StringVar()
        self.wFval2.set(self.param["wFval"][2])
        self.wFval3 = StringVar()
        self.wFval3.set(self.param["wFval"][3])

        self.wFlim0Label = Label(self.wFbox0, text="d < ", justify=LEFT).pack(side=LEFT)
        self.wFlim0Entry = EntryContext(self.wFbox0, width=5, textvariable=self.wFlim0).pack(side=LEFT)
        self.wFval0Label = Label(self.wFbox0, text="*d_max=", justify=LEFT).pack(side=LEFT)
        self.wFval0Entry = EntryContext(self.wFbox0, width=5, textvariable=self.wFval0).pack(side=LEFT)

        self.wFlim0Entry = EntryContext(self.wFbox1, width=5, textvariable=self.wFlim0).pack(side=LEFT)
        self.wFlim0Label = Label(self.wFbox1, text="*d_max <= d < ", justify=LEFT).pack(side=LEFT)
        self.wFlim1Entry = EntryContext(self.wFbox1, width=5, textvariable=self.wFlim1).pack(side=LEFT)
        self.wFval1Label = Label(self.wFbox1, text="*d_max=", justify=LEFT).pack(side=LEFT)
        self.wFval1Entry = EntryContext(self.wFbox1, width=5, textvariable=self.wFval1).pack(side=LEFT)

        self.wFlim0Entry = EntryContext(self.wFbox2, width=5, textvariable=self.wFlim1).pack(side=LEFT)
        self.wFlim0Label = Label(self.wFbox2, text="*d_max <= d < ", justify=LEFT).pack(side=LEFT)
        self.wFlim1Entry = EntryContext(self.wFbox2, width=5, textvariable=self.wFlim2).pack(side=LEFT)
        self.wFval1Label = Label(self.wFbox2, text="*d_max=", justify=LEFT).pack(side=LEFT)
        self.wFval1Entry = EntryContext(self.wFbox2, width=5, textvariable=self.wFval2).pack(side=LEFT)

        self.wFlim2Label = Label(self.wFbox3, text="d >= ", justify=LEFT).pack(side=LEFT)
        self.wFlim2Entry = EntryContext(self.wFbox3, width=5, textvariable=self.wFlim2).pack(side=LEFT)
        self.wFval3Label = Label(self.wFbox3, text="*d_max=", justify=LEFT).pack(side=LEFT)
        self.wFval3Entry = EntryContext(self.wFbox3, width=5, textvariable=self.wFval3).pack(side=LEFT)


        # =======================  Species to Study ===========================
        self.specie_frame = LabelFrame(self.PSCF_frame,
                                       text="Species")
        self.specie_frame.grid(row=3,
                               column=0,
                               columnspan=2,
                               sticky=E+W+S+N,
                               padx=5,
                               pady=5)
        self.species = StringVar()
        allSpecies = ";".join(self.param["species"])
        self.species.set(allSpecies)
        self.speciesLabel = Label(self.specie_frame, text="Specie(s) to study", justify=LEFT)
        self.speciesLabel.grid(row=0, column=0, sticky=W, padx=5, pady=5)
        self.speciesEntry = EntryContext(self.specie_frame, width=40, textvariable=self.species)
        self.speciesEntry.grid(row=0, column=1, sticky=W, padx=5, pady=5)
        # Choice percentile/threshold
        self.percentileBool = BooleanVar()
        self.percentileBool.set(self.param["percentileBool"])
        self.percentileBoolCheck = Checkbutton(self.specie_frame, text="Use the Xth percentile as threshold. If not check, use the threshold.", variable=self.percentileBool, command=self.percentile_callback)
        self.percentileBoolCheck.grid(row=1, column=0, columnspan=60, sticky=W, padx=5, pady=5)
        # Percentile
        self.percentileLabel = Label(self.specie_frame, text="Percentile", justify=LEFT)
        self.percentileLabel.grid(row=2, column=0, sticky=W, padx=5, pady=5)
        self.percentile = StringVar()
        self.percentile.set(self.param["percentile"])
        self.percentileEntry = EntryContext(self.specie_frame, width=30, textvariable=self.percentile)
        self.percentileEntry.grid(row=2, column=1, sticky=W, padx=5, pady=5)
        # threshold
        self.threshold = StringVar()
        self.threshold.set(self.param["threshold"])
        self.thresholdLabel = Label(self.specie_frame, text="Threshold", justify=LEFT)
        self.thresholdLabel.grid(row=3, column=0, sticky=W, padx=5, pady=5)
        self.thresholdEntry = EntryContext(self.specie_frame, width=30, textvariable=self.threshold)
        self.thresholdEntry.grid(row=3, column=1, sticky=W, padx=5, pady=5)

        # ===== Time frame                          ===========================
        self.time_frame = LabelFrame(self.PSCF_frame,
                                     text="Date")
        self.time_frame.grid(row=3,
                             column=2,
                             sticky=E+W+S+N,
                             padx=5,
                             pady=5)
        self.labelTimeFrame = Label(self.time_frame, text="Choose the limits dates from when to when\n the back-trajectories are computed.", justify=LEFT)
        self.labelTimeFrame.grid(row=0, column=0, columnspan=2, sticky=E+W+S+N)
        # Start time
        self.startLabel = Label(self.time_frame, text="From... ", justify=LEFT)
        self.startLabel.grid(row=1, column=0, sticky=E+W+S+N,
                             padx=5, pady=5)
        self.buttonMin = Frame(self.time_frame)
        self.buttonMin.grid(row=1, column=1, sticky=W+E+S+N, padx=5, pady=5)
        self.dateMin = StringVar()
        self.dateMin.set(self.param["dateMin"])
        self.dateMinLabel = Label(self.buttonMin, text="YYYY-MM-DD:", justify=LEFT).pack(side=LEFT)
        self.dateMinEntry = EntryContext(self.buttonMin, width=10,
                                         textvariable=self.dateMin).pack(side=LEFT)
        # End time
        self.endLabel = Label(self.time_frame, text="To... ", justify=LEFT)
        self.endLabel.grid(row=2, column=0,
                           sticky=E+W,
                           padx=5, pady=0)
        self.buttonMax = Frame(self.time_frame)
        self.buttonMax.grid(row=2, column=1, sticky=W+E, padx=5, pady=5)
        self.dateMax = StringVar()
        self.dateMax.set(self.param["dateMax"])
        self.dateMaxLabel = Label(self.buttonMax, text="YYYY-MM-DD:", justify=LEFT).pack(side=LEFT)
        self.dateMaxEntry = EntryContext(self.buttonMax, width=10,
                                         textvariable=self.dateMax).pack(side=LEFT)

        # ==================== Miscellaneous ==================================
        self.BT_frame = LabelFrame(self.PSCF_frame,
                                   text="Miscallaneous")
        self.BT_frame.grid(row=4,
                           column=0,
                           columnspan=3,
                           sticky=E+W+S+N,
                           padx=5,
                           pady=5)

        self.areaPack = Frame(self.BT_frame)
        self.areaPack.grid(row=0, column=0, columnspan=3, sticky=E+W, padx=5, pady=5)
        self.LatMin = StringVar()
        self.LatMax = StringVar()
        self.LonMin = StringVar()
        self.LonMax = StringVar()
        self.LatMin.set(self.param["mapMinMax"]["latmin"])
        self.LatMax.set(self.param["mapMinMax"]["latmax"])
        self.LonMin.set(self.param["mapMinMax"]["lonmin"])
        self.LonMax.set(self.param["mapMinMax"]["lonmax"])
        self.areaLonMinLabel = Label(self.areaPack, text='Lon min', justify=LEFT).pack(side=LEFT)
        self.areaLonMinEntry = EntryContext(self.areaPack, width=5, textvariable=self.LonMin).pack(side=LEFT)
        self.areaLonMaxLabel = Label(self.areaPack, text='Lon max', justify=LEFT).pack(side=LEFT)
        self.areaLonMaxEntry = EntryContext(self.areaPack, width=5, textvariable=self.LonMax).pack(side=LEFT)
        self.areaLatMinLabel = Label(self.areaPack, text='Lat min', justify=LEFT).pack(side=LEFT)
        self.areaLatMinEntry = EntryContext(self.areaPack, width=5, textvariable=self.LatMin).pack(side=LEFT)
        self.areaLatMaxLabel = Label(self.areaPack, text='Lat max', justify=LEFT).pack(side=LEFT)
        self.areaLatMaxEntry = EntryContext(self.areaPack, width=5, textvariable=self.LatMax).pack(side=LEFT)

        self.plotBT = BooleanVar()
        self.plotBT.set(self.param["plotBT"])
        self.plotBTCheck = Checkbutton(self.BT_frame, text="Plot the back-traj", variable=self.plotBT)
        self.plotBTCheck.grid(row=1, column=0, sticky=W, padx=5, pady=5)
        self.plotPolar = BooleanVar()
        self.plotPolar.set(self.param["plotPolar"])
        self.plotPolarCheck = Checkbutton(self.BT_frame, text="Plot the polar plot", variable=self.plotPolar)
        self.plotPolarCheck.grid(row=1, column=1, sticky=W, padx=5, pady=5)
        self.smoothplot = BooleanVar()
        self.smoothplot.set(self.param["smoothplot"])
        self.smoothplotCheck = Checkbutton(self.BT_frame, text="smooth the result", variable=self.smoothplot)
        self.smoothplotCheck.grid(row=1, column=2, sticky=W, padx=5, pady=5)
        self.resLabel = Label(self.BT_frame, text="Background resolution", justify=LEFT)
        self.resLabel.grid(row=1, column=3, sticky=W, padx=5, pady=5)
        self.resQuality = StringVar()
        self.resQuality.set(self.param["resQuality"])
        self.resQualityChoice = OptionMenu(self.BT_frame, self.resQuality,
                                           self.param["resQuality"],
                                           "110m", "50m", "10m")
        self.resQualityChoice.grid(row=1, column=4, sticky=W, padx=5, pady=5)

        # ===== First check ==================================================
        self.wf_callback(self.wf_frame)
        self.percentile_callback()
        self.exist_file()

        # ===== column config ================================================
        self.columnconfigure(0, weight=10)
        self.PSCF_frame.columnconfigure(0, weight=10)
        self.PSCF_frame.columnconfigure(1, weight=10)
        self.PSCF_frame.columnconfigure(2, weight=10)
        self.rowconfigure(0, weight=10)
        self.PSCF_frame.rowconfigure(0, weight=10)
        self.PSCF_frame.rowconfigure(1, weight=10)
        self.PSCF_frame.rowconfigure(2, weight=10)
        self.PSCF_frame.rowconfigure(3, weight=10)
        self.PSCF_frame.rowconfigure(4, weight=10)

    def check_param(self):
        errorCode = self.on_save()
        if errorCode == 0:
            return 1
        threshold = json2arr(self.param["threshold"], np.float64)
        percentile = json2arr(self.param["percentile"], np.float64)
        # Check Path
        if not os.path.exists(self.param["dirBackTraj"]):
            showinfo("""Error""", """The back traj directory does not exist""")
            return 0
        if not os.path.exists(self.param["Cfile"]):
            showinfo("""Error""", """The concentration file does not exist""")
            return 0
        # Check wf
        # TODO
        # Check Species
        f = open(self.param["Cfile"]).readlines()
        text="The specie \"{specie}\" is not found in the concentration file."
        for specie in self.param["species"]:
            if not any([specie in ff for ff in f]):
                showinfo("""Error""", text.format(specie=specie))
                return 0

        #     sp  = specie2study(self.param["Cfile"], specie)
        #     if sp == -999:
        #         header=np.genfromtxt(self.param["Cfile"], delimiter=';', max_rows=1, dtype=str)
        #         showinfo("""Error""", text) 
        #         return 0
        # Check length of parameter
        if (len(self.param["species"]) != len(threshold)) and not self.param["percentileBool"] and (len(threshold) != 1):
            showinfo("""Error""", """The number of specie and threshold must match or the threshold must be unique.""")
            return 0
        elif (len(self.param["species"]) != len(percentile)) and self.param["percentileBool"] and (len(percentile) != 1):
            showinfo("""Error""", """The number of specie and percentile must match or the percentile must be unique.""")
            return 0

        return 1

    def on_save(self):
        with open('parameters'+os.sep+'localParamPSCF_tmp.json', 'w') as fileSave:
            try:
                paramNew = {
                    "dirBackTraj": self.dirBackTraj.get(),
                    "Cfile": self.Cfile.get(),
                    "station": self.station.get(),
                    "prefix": self.prefixTraj.get(),
                    "backTraj": self.backTraj.get(),
                    "add_hour": arr2json(np.array(literal_eval(self.add_hour.get()))),
                    "dateMin": self.dateMin.get(),
                    "dateMax": self.dateMax.get(),
                    "species": self.species.get().split(';'),
                    "threshold": arr2json(np.array(literal_eval(self.threshold.get()))),
                    "percentileBool": self.percentileBool.get(),
                    "percentile": arr2json(np.array(literal_eval(self.percentile.get()))),
                    "wF": self.weigthingFunction.get(),
                    "wFmanual": self.wf_manual.get(),
                    "wFlim": [self.wFlim0.get(), self.wFlim1.get(), self.wFlim2.get()],
                    "wFval": [self.wFval0.get(), self.wFval1.get(), self.wFval2.get(), self.wFval3.get()],
                    "smoothplot": self.smoothplot.get(),
                    "plotBT": self.plotBT.get(),
                    "plotPolar": self.plotPolar.get(),
                    "resQuality": self.resQuality.get(),
                    "cutWithRain": self.cutWithRain.get(),
                    "mapMinMax": {
                        "latmin": float(self.LatMin.get()),
                        "latmax": float(self.LatMax.get()),
                        "lonmin": float(self.LonMin.get()),
                        "lonmax": float(self.LonMax.get()),
                    },
                }
            except (ValueError, SyntaxError):
                # If a string is somewhere in the np.array it gives an error due to arr2json
                # or if a bracket is missing somewhere
                os.remove('parameters'+os.sep+'localParamPSCF_tmp.json')
                showinfo("""Error""", """There is a problem somewhere... Probably a typo in "Add hour", "Percentile" or "Threshold". The 'parameters'+os.sep+'localParamPSCF.json' file is not updated due to this problem.""")
                return 0
            json.dump(paramNew, fileSave, indent=4)
        shutil.copy('parameters'+os.sep+'localParamPSCF_tmp.json',
                    'parameters'+os.sep+'localParamPSCF.json')
        os.remove('parameters'+os.sep+'localParamPSCF_tmp.json')
        # update the "param" dict.
        self.param = paramNew
        return 1

    def setState(self, widget, state='disabled'):
        try:
            widget.configure(state=state)
        except TclError:
            pass
        for child in widget.winfo_children():
            self.setState(child, state=state)

    def wf_callback(self, *arg):
        if self.weigthingFunction.get():
            self.wf_manual_callback(self.wf_frame_manual_choice)
        else:
            self.setState(self.wf_frame_manual_choice)

    def wf_manual_callback(self, *arg):
        var = self.varChoiceManual.get()
        if var == "User defined" and self.weigthingFunction.get():
            self.wf_manual.set("true")
            self.setState(self.wf_frame_manual_choice, state="normal")
        else:
            self.wf_manual.set("false")
            self.setState(self.wf_frame_manual_choice)

    def percentile_callback(self):
        if self.percentileBool.get():
            self.setState(self.thresholdEntry)
            self.setState(self.percentileEntry, state="normal")
        else:
            self.setState(self.thresholdEntry, state="normal")
            self.setState(self.percentileEntry)

    def station_callback(self, event):
        with open(os.path.normpath('parameters/locationStation.json'), 'r') as dataFile:
            locStation = json.load(dataFile)
        self.lat0.set(locStation[self.station.get()][0])
        self.lon0.set(locStation[self.station.get()][1])
        self.prefixTraj.set("traj_"+self.station.get()+"_")
        self.Cfile.set(os.path.dirname(self.Cfile.get())+os.sep+self.station.get()+'.csv')
        self.dirBackTraj.set(os.path.normpath(self.dirBackTraj.get()+os.sep+'..'+os.sep+self.station.get())+os.sep)
        self.exist_file()

    def exist_file(self):
        if not os.path.exists(self.dirBackTraj.get()):
            self.dirBackTrajSelect.dir_entry.config(foreground='red')
        else:
            self.dirBackTrajSelect.dir_entry.config(foreground='black')
        if not os.path.isfile(self.Cfile.get()):
            self.CfileSelect.dir_entry.config(foreground='red')
        else:
            self.CfileSelect.dir_entry.config(foreground='black')


class aboutTab(Frame):
    def __init__(self, parent):
        if sys.version_info.major >= 3:
            super().__init__(parent)
        else:
            Frame.__init__(self, parent)

        self.text_frame = LabelFrame(self,
                                     text="About this GUI")
        self.text_frame.grid(row=0,
                             column=0,
                             sticky=N+E+S+W)

        data = """This GUI is an adapted GUI from the game "The Battle For Westnoth", developed by Elvish_Hunter, 2014-2015,\n under the GNU GPL v2 license.\n
Original PSCF script: Jean-Eudes PETIT \n
New PSCF script and GUI tools : Samuel WEBER\n
Icons are taken from the Tango Desktop Project (http://tango.freedesktop.org) and are released in the Public Domain."""
        text = Label(self.text_frame, text=data)
        text.grid(row=0,
                  column=0,
                  sticky=N+E+S+W)

        # use a proportional font to handle spaces correctly
        text.config(font=('Arial', 12))

        self.columnconfigure(0, weight=10)
        self.text_frame.columnconfigure(0, weight=10)


class MainFrame(Frame):
    def __init__(self, parent):
        self.parent = parent
        if sys.version_info.major >= 3:
            super().__init__(parent)
        else:
            Frame.__init__(self, parent)

        self.grid(sticky=N+E+S+W)

        self.buttonBox = Frame(self)
        self.buttonBox.grid(row=0,
                            column=0,
                            sticky=E+W)
        self.run_button = Button(self.buttonBox,
                                 text="Run PSCF",
                                 image=ICONS['run'],
                                 compound=LEFT,
                                 width=15, # to avoid changing size when callback is called
                                 command=self.on_run_PSCF)
        self.run_button.pack(side=LEFT, padx=5, pady=5)
        self.save_button = Button(self.buttonBox,
                                  text="Save param",
                                  image=ICONS['save'],
                                  compound=LEFT,
                                  command=self.on_save)
        self.save_button.pack(side=LEFT, padx=5, pady=5)
        self.exit_button = Button(self.buttonBox,
                                  text="Exit",
                                  image=ICONS['exit'],
                                  compound=LEFT,
                                  command=parent.destroy)
        self.exit_button.pack(side=RIGHT, padx=5, pady=5)


        # ===== NoteBook =====================================================
        self.notebook = Notebook(self)
        self.notebook.grid(row=1,
                           column=0,
                           sticky=E+W)
        # BackTraj calculation
        self.backtraj_tab = BacktrajTab(None)
        self.notebook.add(self.backtraj_tab,
                          text="Back-Trajectory",
                          sticky=N+E+S+W)
        # PSCF
        self.PSCF_tab = PSCFTab(None)
        self.notebook.add(self.PSCF_tab,
                          text="PSCF",
                          sticky=N+E+S+W)
        # Output
        # self.output_tab=TextoutputTab(None)
        # self.notebook.add(self.output_tab,
        #                  text="Output",
        #                  sticky=N+E+S+W)

        # Station param
        self.station_tab = StationTab(None)
        self.notebook.add(self.station_tab,
                          text="Stations param.",
                          sticky=N+E+S+W)
        # Info & about
        self.about_tab = aboutTab(None)
        self.notebook.add(self.about_tab,
                          text="About",
                          sticky=N+E+S+W)

        # ===== Text ========================================================
        # self.text = tkst.ScrolledText(self,
        #                              wrap="word",
        #                               width  = 200,
        #                               height = 10)
        # self.text.grid(row=2,
        #                column=0,
        #               sticky=N+E+S+W)
        # self.text.tag_configure("stderr", foreground="#b22222")

        self.columnconfigure(0, weight=10)
        self.rowconfigure(0, weight=10)
        self.rowconfigure(1, weight=10)
        self.rowconfigure(2, weight=10)

        # this allows using the mouse wheel even on the disabled Text widget
        # without the need to clic on said widget
        # self.tk_focusFollowsMouse()

        self.notebook.bind("<<NotebookTabChanged>>", self.tab_callback)

    def tab_callback(self, event):
        # we check the ID of the active tab and ask its position
        # the order of the tabs is pretty obvious
        active_tab=self.notebook.index(self.notebook.select())
        if active_tab == 0:
            self.run_button.configure(text="Run Back-traj", command=self.on_run_backtraj)
            self.save_button.configure(text="Save BackTraj")
        elif active_tab == 1:
            self.run_button.configure(text="Run PSCF", command=self.on_run_PSCF)
            self.save_button.configure(text="Save PSCF")

    def on_clear(self):
        self.text.configure(state=NORMAL)
        self.text.delete(1.0, END)
        self.text.configure(state=DISABLED)

    def on_save(self):
        # we check the ID of the active tab and ask its position
        # the order of the tabs is pretty obvious
        active_tab = self.notebook.index(self.notebook.select())
        if active_tab == 0:
            self.backtraj_tab.on_save()
        elif active_tab == 1:
            self.PSCF_tab.on_save()




    def on_run_PSCF(self):
        errorCode = self.PSCF_tab.check_param()
        if errorCode == 0:
            return
        # Run PSCF
        with open('parameters'+os.sep+'localParamPSCF.json', 'r') as dataFile:
            param = json.load(dataFile)



        # change tab
        # self.notebook.select(2)
        print("PSCF starts... Please wait.")
        for specie in range(len(param["species"])):
            args = dict(
                station=param["station"],
                specie=param["species"][specie],
                lat0=self.PSCF_tab.locStation[param["station"]][0],
                lon0=self.PSCF_tab.locStation[param["station"]][1],
                folder=param["dirBackTraj"],
                prefix=param["prefix"],
                add_hour=json2arr(param["add_hour"], np.float),
                resQuality=param["resQuality"],
                percentile=json2arr(param["percentile"], np.float),
                threshold=json2arr(param["threshold"], np.float),
                concFile=param["Cfile"],
                dateMin=param["dateMin"],
                dateMax=param["dateMax"],
                wfunc=param["wF"],
                wfunc_type="manual" if param["wFmanual"] else "auto",
                smoothplot=param["smoothplot"],
                mapMinMax=param["mapMinMax"],
                cutWithRain=param["cutWithRain"],
                hourinthepast=param["backTraj"],
                plotBT=param["plotBT"],
                plotPolar=param["plotPolar"],
                pd_kwarg={"sep": ";"}
            )
            for var in ["threshold", "percentile"]:
                if (len(param["species"])>1) & (len(args[var])>1):
                    args[var] = args[var][specie]
                else:
                    args[var] = args[var][0]
            if param["percentileBool"]:
                args["threshold"] = None
            else:
                args["percentile"] = None

            model = pyPSCF.PSCF(**args)
            # args should follow the init signature of pyPSCF.PSCF

            model.run()
            if model.plotBT:
                model.plot_backtraj()
            if model.plotPolar:
                model.plot_PSCF_polar()
            model.plot_PSCF()
        plt.show()

    def on_run_backtraj(self):
        # check
        errorCode = self.backtraj_tab.on_save()
        if errorCode == 0:
            return
        errorCode, nbCPU = self.backtraj_tab.checkParam()
        if errorCode == 0:
            return
        # change tab
        # self.notebook.select(2)
        # Compute the Back Traj
        for i in range(nbCPU):
            time.sleep(1)
            p = Process(target=BT)
            p.start()
        # block until the last process finish
        p.join()

        showinfo("""Done!""", """The back-trajectory script is finish. See the terminal output if error was raised.""")

if __name__ == '__main__':
    root = Tk()

    ICONS = {
               "about": PhotoImage(data=b'''
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
        "run": PhotoImage(data=b'''
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
        "save": PhotoImage(data=b'''
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
    "exit": PhotoImage(data=b'''
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
               "browse": PhotoImage(data=b'''
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
               "clear16": PhotoImage(data=b'''
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
               "cut": PhotoImage(data=b'''
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
               "copy": PhotoImage(data=b'''
    R0lGODlhEAAQAKUeAIiKhYmLhoyOiZialZialpyemqGjn6mqp62uq6+wrbu8ury9ur2+u8PEw8fH
    xs/QzdDRz9TU1NnZ2dra2tvb2+Pj4uPk4uzs7O3t7e7u7e7u7u/v7u/v7/Dw7/Dw8PHx8PHx8fPz
    8/T09Pb29fb29vf39vf39/j49/r6+fr6+vv7+/z8+/7+/f////Dw8PDw8PDw8PDw8PDw8PDw8PDw
    8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8CH5BAEKAD8ALAAAAAAQABAAAAaKQIhi
    SCw+fsgfw8RsOhVJpYmzqVY5HBM0ueRQDoCweIzocgKttHoN6FIArY58Lm+1pxt0x8Hvd+xLGxNw
    dHSAJhoZen18dW0kGBKEhR0pIW0iGBeLjBolDW0fIB56dAKnAgAQC6wALHQpAyknFgBRAShzKbEp
    FQAFtyIlIysqEQS1W0kJAWNhBltBADs='''),
               "paste": PhotoImage(data=b'''
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
               "select_all": PhotoImage(data=b'''
    R0lGODlhEAAQAKUZAAAAAIeJhIiKhYqMh4uNiIGXr4KYsLS1s7W2s7W2tKi+1qm/16rA2KvB2azC
    2q3D267E3K/F3bDG3rHH37LI4LPJ4evr6+zs7O7u7vDw8PLy8vT09PX19fb29vf39/j4+Pn5+fr6
    +vv7+/z8/P39/f7+/vDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw
    8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8CH5BAEKAD8ALAAAAAAQABAAAAaWwN9B
    QCwaiYjfL0AqlUik0UgkCoVAA6WApFgsGIyGWPwhaEuLgrrgWDvKWhJjXXjY7fDfdr5+QP4WeQIj
    DXQQahEXgiMODn4RERKSGIuOEJCSExMZgiJtdGoUGh5meiKPkgAUABUbpFohqBOrHB0dr3ogDwa8
    BqseHx64ArqXErMAHiDBpQEfz9AAH9LPWT8IR9kCCT9BADs=''')
               }


    ROOT_W, ROOT_H=900,640
    # the following string may be confusing, so here there's an explanation
    # Python supports two ways to perform string interpolation
    # the first one is the C-like style
    # the second one is the following, where each number enclosed in brackets points to an argument of the format method
    root.geometry("{0}x{1}+{2}+{3}".format(ROOT_W,
        ROOT_H,
        int((root.winfo_screenwidth()-ROOT_W)/2),
        int((root.winfo_screenheight()-ROOT_H)/2)))

    root.title("PSCF GUI")
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)
    # use a better style on Linux instead of the Motif-like one
    style=Style()
    if sys.platform.startswith("linux") and "clam" in style.theme_names():
        style.theme_use("clam")

    app=MainFrame(root)

    def redirector(inputStr):
        app.output_tab.output_text.insert(INSERT, inputStr)
    #Redirect stdout/stderr to text
    #sys.stdout.write = redirector
    #sys.stderr.write = redirector

    print("==== Welcome to the PSCF GUI ====")
    root.mainloop()
    sys.exit(0)
