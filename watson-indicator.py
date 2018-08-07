#!/usr/bin/env python3
import os
import signal
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GObject
import time
from threading import Thread
from subprocess import check_output, Popen

class Indicator():
    def __init__(self):
        self.app = "watson-indicator"
        # icons
        dirname = os.path.dirname(os.path.abspath(__file__))
        self.icon_passive = os.path.join(dirname, "assets/task_passive.png")
        self.icon_active = os.path.join(dirname, "assets/task_active.png")
        self.indicator = AppIndicator3.Indicator.new(self.app, self.icon_passive, AppIndicator3.IndicatorCategory.OTHER)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.create_menu())
        # variables
        self.old_msg = ""
        self.old_task_active = False # if a task is active
        self.indicator.set_label(self.old_msg, self.app)
        self.last_task = "?" # last active task (important for restarting the last task
        # the thread:
        self.update = Thread(target=self.update)
        # daemonize the thread to make the indicator stopable
        self.update.setDaemon(True)
        self.update.start()

    def stop_restart(self, source):
        if self.old_task_active: # if task is running, stop it
            Popen(["watson", "stop"])
        else: # if no task is running, restart the last one
            Popen(["watson", "restart"])


    def create_menu(self):
        menu = Gtk.Menu()
        # menu item "Stop/Restart task"
        self.item_stop_restart = Gtk.MenuItem("Loading...")
        self.item_stop_restart.connect('activate', self.stop_restart)
        menu.append(self.item_stop_restart)
        item_quit = Gtk.MenuItem('Quit')
        item_quit.connect('activate', self.quit)
        menu.append(item_quit)
        menu.show_all()
        return menu

    def update(self):
        # updates the icon, indicator and menu item labels
        while True:
            time.sleep(1)
            msg = check_output(["watson", "status"])
            if "No project started" in msg:
                msg = ""
                task_active = False
            else:
                # "Starting project xy at 09:09"
                start = msg.index("roject") + 7
                end = msg.index(" ", start)
                self.last_task = msg[start:end]
                msg = " " + self.last_task
                task_active = True

            # check if different message
            if msg != self.old_msg:
                self.old_msg = msg
                # change label
                GObject.idle_add(
                    self.indicator.set_label,
                    msg, self.app,
                    priority=GObject.PRIORITY_DEFAULT
                    )
            # check if different task_active
            if task_active != self.old_task_active:
                self.old_task_active = task_active
                # change icon
                GObject.idle_add(
                    self.indicator.set_icon,
                    self.icon_active if task_active else self.icon_passive)
                # change item label in menu
                text = "Stop" if task_active else ("Restart '" + self.last_task + "'")
                GObject.idle_add(
                    self.item_stop_restart.get_child().set_text,
                    text)


    def quit(self, source):
        Gtk.main_quit()


Indicator()
# this is where we call GObject.threads_init()
GObject.threads_init()
signal.signal(signal.SIGINT, signal.SIG_DFL)
Gtk.main()
