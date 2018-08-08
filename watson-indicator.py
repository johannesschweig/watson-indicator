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
        self.icon_passive = os.path.join(dirname, "assets/project_passive.png")
        self.icon_active = os.path.join(dirname, "assets/project_active.png")
        self.indicator = AppIndicator3.Indicator.new(self.app, self.icon_passive, AppIndicator3.IndicatorCategory.OTHER)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.create_menu())
        # variables
        self.old_project = ""
        self.old_project_active = False # if a project is active
        self.indicator.set_label(self.old_project, self.app)
        self.last_project = "?" # last active project (important for restarting the last project)
        # the thread:
        self.update = Thread(target=self.update)
        # daemonize the thread to make the indicator stopable
        self.update.setDaemon(True)
        self.update.start()

    def stop_restart(self, source):
        if self.old_project: # if project is running, stop it
            Popen(["watson", "stop"])
        else: # if no project is running, restart the last one
            Popen(["watson", "restart"])


    def create_menu(self):
        menu = Gtk.Menu()
        # menu item "Stop/Restart project"
        self.item_stop_restart = Gtk.MenuItem("Loading...")
        self.item_stop_restart.connect('activate', self.stop_restart)
        menu.append(self.item_stop_restart)
        item_quit = Gtk.MenuItem('Quit')
        item_quit.connect('activate', self.quit)
        menu.append(item_quit)
        menu.show_all()
        return menu

    def update_label(self, project):
        # check if different project
        if project != self.old_project:
            self.old_project = project
            # change label
            GObject.idle_add(self.indicator.set_label, project, self.app, priority=GObject.PRIORITY_DEFAULT)

    # update icon
    def update_icon(self, project_active):
        # check if different project_active
        if project_active != self.old_project_active:
            self.old_project_active = project_active
            # change icon
            GObject.idle_add(self.indicator.set_icon, self.icon_active if project_active else self.icon_passive)

    # updates the label of the stop/restart menuitem
    def update_stop_restart_label(self, project_active):
        text = ""
        if project_active: # stop project (time)
            text = "Stop (" + check_output(["watson", "status", "-e"]).strip() + ")"
            text = text.replace("minutes ago", "min")
        else: # restart project
            text = "Restart '" + self.last_project + "'"
        # change item label in menu
        GObject.idle_add(self.item_stop_restart.get_child().set_text, text)


    def update(self):
        # updates the icon, indicator and menu item labels
        while True:
            time.sleep(1)
            # "project" or "No project started"
            project = check_output(["watson", "status", "-p"]).strip()
            if "No project started" in project:
                project = ""
                project_active = False
            else:
                self.last_project = project
                project = " " + self.last_project
                project_active = True

            # update indicator label
            self.update_label(project)
            # update indicator icon
            self.update_icon(project_active)
            # update time and project in stop/restart label
            self.update_stop_restart_label(project_active)


    def quit(self, source):
        Gtk.main_quit()


Indicator()
# this is where we call GObject.threads_init()
GObject.threads_init()
signal.signal(signal.SIGINT, signal.SIG_DFL)
Gtk.main()
