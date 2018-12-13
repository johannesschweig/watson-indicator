#!/usr/bin/env python3
import os
import signal
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GObject
import time
from threading import Thread
from subprocess import getoutput, Popen, check_output
import json
from datetime import datetime


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
        self.issues = self.get_issues() # list of open issues
        # the thread:
        self.update = Thread(target=self.update)
        # daemonize the thread to make the indicator stopable
        self.update.setDaemon(True)
        self.update.start()

    # get list of issues
    def get_issues(self):
        # get open firefox tab issues
        ## load data from firefox profile
        data = json.loads(check_output(['/home/jschweig/misc/lz4json/lz4jsoncat', '/home/jschweig/.mozilla/firefox/o5ngtz92.default/sessionstore-backups/recovery.jsonlz4']))

        ## list of jira tickets in open firefox tabs
        tickets = []

        for tab_obj in data['windows'][0]['tabs']:
            for entry in tab_obj['entries']:
                # if tab is jira issue
                if (entry['url'].startswith('https://knime-com.atlassian.net/browse/')):
                    ticket = entry['title'].replace(' - JIRA', '')
                    if len(ticket) > 30:
                        ticket = ticket[:30] + '...'
                    tickets.append(ticket)
        return tickets

    # start working on issue
    # widget: reference to the widget where the function was triggered (Don't know how to avoid this)
    # issue_code: issue code of the ticket to be started
    def start_issue(self, widget, issue_code):
        Popen(['watson', 'start', issue_code, '+verification', '+scrum'])

    # get ticket submenu
    # show: if there should be a separate show call for the menuitems
    def get_tickets(self, show):
        # create menu
        item_start_ticket = Gtk.MenuItem('Start ticket')
        menu_tickets = Gtk.Menu()
        for ticket in self.get_issues():
            item = Gtk.MenuItem(ticket)
            menu_tickets.append(item)
            # get code of issue
            i = ticket.find(']')
            issue_code = ticket[1:i]
            item.connect('activate', self.start_issue, issue_code)
            if show:
                item.show()
        item_start_ticket.set_submenu(menu_tickets)
        return item_start_ticket

    # stops a project (if one is running) or restarts the last one
    def stop_restart(self, source):
        if self.old_project: # if project is running, stop it
            Popen(["watson", "stop"])
        else: # if no project is running, restart the last one
            Popen(["watson", "restart"])

    def test(self):
        print('test')

    # creates the top menu for the application indicator
    def create_menu(self):
        self.menu = Gtk.Menu()
        # menu item "Stop/Restart project"
        self.item_stop_restart = Gtk.MenuItem("Loading...")
        self.item_stop_restart.connect('activate', self.stop_restart)
        self.menu.append(self.item_stop_restart)
        # menu item "Start ticket"
        self.item_start_ticket = self.get_tickets(False)
        self.menu.append(self.item_start_ticket)
        # menu item "Quit"
        item_quit = Gtk.MenuItem('Quit')
        item_quit.connect('activate', self.quit)
        self.menu.append(item_quit)

        self.menu.show_all()
        return self.menu

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
            text = "Stop (" + getoutput("watson status -e").strip() + ")"
            text = text.replace("minutes ago", "min")
        else: # restart project
            text = "Restart '" + self.last_project + "'"
        # change item label in menu
        GObject.idle_add(self.item_stop_restart.get_child().set_text, text)

    # updates the start ticket menu
    def update_tickets(self):
        new_issues = self.get_issues()
        if new_issues != self.issues:
            self.issues = new_issues
            GObject.idle_add(self.menu.remove, self.item_start_ticket)
            self.item_start_ticket = self.get_tickets(True)
            GObject.idle_add(self.menu.insert, self.item_start_ticket, 1)
            self.item_start_ticket.show()

    def update(self):
        # updates the icon, indicator and menu item labels
        while True:
            time.sleep(1)
            # "project" or "No project started"
            project = getoutput("watson status -p").strip()
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
            # update tickets in 'Start ticket'
            self.update_tickets()

    def quit(self, source):
        Gtk.main_quit()


Indicator()
GObject.threads_init()
signal.signal(signal.SIGINT, signal.SIG_DFL)
Gtk.main()
