#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    import gtk
except:
    pass
import notify2
import os
import time
from signal import SIGTERM
import errno
import sys
import traceback
import ConfigParser
import json
from icons import *


class vpn_lib:
    def __init__(self, homeDir, scriptName, textonly=False, debug=False, noicon=False):
        self.homeDir = homeDir
        self.scriptName = scriptName
        self.textonly = textonly
        self.debug = debug
        self.noicon = noicon
        self.pidfile = self.homeDir + "/" + self.scriptName + ".pid"
        self.config = ConfigParser.ConfigParser()
        self.config.read(self.homeDir + "/" + self.scriptName + ".secret")
        if not self.textonly and not self.debug:
            # create a new window
            self.statusIcon = gtk.StatusIcon()
            self.statusIcon.connect('popup-menu', self.on_right_click)
            notify2.init(self.scriptName)

    def getTokenPass(self, tokenPass):
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_size_request(350, 60)
        window.set_position(gtk.WIN_POS_CENTER)
        window.set_title(self.scriptName + ", PIN from token:")
        window.connect("delete_event", lambda w, e: gtk.main_quit())

        vbox = gtk.VBox(False, 0)
        window.add(vbox)
        vbox.show()

        entry = gtk.Entry()
        entry.set_max_length(50)
        entry.connect("activate", self.myCallback, entry, window, tokenPass)
        vbox.pack_start(entry, True, True, 0)
        entry.show()

        hbox = gtk.HBox(False, 0)
        vbox.add(hbox)
        hbox.show()

        button = gtk.Button(stock=gtk.STOCK_CANCEL)
        # button.connect("clicked", lambda w: quit())
        button.connect("clicked", lambda w: sys.exit(2))
        hbox.pack_start(button, True, True, 0)
        button.set_flags(gtk.CAN_DEFAULT)
        button.grab_default()
        button.show()

        button = gtk.Button(stock=gtk.STOCK_OK)
        button.connect("clicked", self.myCallback, entry, window, tokenPass)
        hbox.pack_start(button, True, True, 0)
        button.set_flags(gtk.CAN_DEFAULT)
        button.grab_default()
        button.show()

        window.show()

    def myCallback(self, widget, entry, window, tokenPass):
        tokenPass[0] = entry.get_text()
        tokenPass[0] = "".join(tokenPass[0].split())
        window.destroy()
        if len(tokenPass[0]) != 6:
            self.message(data="Bad tokena length")
            sys.exit(1)
        if not tokenPass[0].isdigit():
            self.message(data="Bad chars in token")
            sys.exit(1)
        gtk.main_quit()

    def message(self, data=None, type=gtk.BUTTONS_CLOSE):
        msg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, type, data)
        rval = msg.run()
        msg.destroy()
        return rval

    def set_icon(self, icon_file):
        self.statusIcon.set_from_file(icon_file)

    def make_menu(self, event_button, event_time, data=None):
        menu = gtk.Menu()
        close_item = gtk.MenuItem("Close " + self.scriptName)
        menu.append(close_item)
        # add callback
        close_item.connect_object("activate", self.close_app, "Really close " + self.scriptName + "?")
        close_item.show()
        # Popup the menu
        menu.popup(None, None, None, event_button, event_time)

    def on_right_click(self, data, event_button, event_time):
        self.make_menu(event_button, event_time)

    def close_app(self, data=None):
        pidfile = self.homeDir + "/" + self.scriptName + ".pid"
        if os.path.exists(pidfile):
            os.remove(pidfile)
        self.sysCmds("postVPNstop")
        sys.exit(0)

    def checkPidFile(self):
        msg = [
                "pidfile " + self.pidfile + " exists!",
                "Connection is already established or\npreceding terminated with error.\nCheck processes and delete file."
              ]
        if os.path.exists(self.pidfile):
            if self.textonly or self.debug:
                print msg[0], msg[1]
            else:
                n = notify2.Notification(msg[0], msg[1], errorIcon)
                n.set_urgency(2)
                n.show()
            sys.exit(1)

    def sysCmds(self, section):
        try:
            cmds = json.loads(self.config.get(section, "systemCMD"))
            if self.textonly or self.debug:
                print "\n", section + ":"
            for cmd in cmds:
                if self.textonly or self.debug:
                    print " ", cmd
                try:
                    os.system(cmd)
                except Exception:
                    print traceback.format_exc()
                    raise
        except:
            pass

    def killVpn(self):
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:
            msg = ["pidfile " + self.pidfile + " does not exists!", "Has been deleted?\nClose connection by killing process"]
            if self.textonly or self.debug:
                print msg[0], msg[1]
            else:
                n = notify2.Notification(msg[0], msg[1], errorIcon)
                n.set_urgency(2)
                n.show()
            sys.exit(1)

        try:
            self.sysCmds("preVPNstop")
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            if err.errno == errno.ESRCH:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
                    msg = "Closed VPN connection: " + self.scriptName
                    if self.textonly or self.debug:
                        print msg
                    else:
                        n = notify2.Notification(msg, "", connectingIcon)
                        n.show()
                    self.sysCmds("postVPNstop")
            else:
                n = notify2.Notification(str(err))
                n.set_urgency(2)
                n.show()
                sys.exit(1)

