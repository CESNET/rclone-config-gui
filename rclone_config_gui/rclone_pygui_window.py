#
# Copyright (C) 2025 CESNET
#
# rclone_config_gui is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

""" S3 rclone config GUI window """

import sys, os, platform
from PySide6.QtWidgets import QMainWindow, QMessageBox
from PySide6.QtGui import QAction, QIcon, QShortcut, QKeySequence
from types import SimpleNamespace as nspace
import boto3

from .utils import WarningQD
from .version import __version__
from .rclone_control import Rclone_control
from .rclone_pygui_lib import MainWidget

class MainWindow(QMainWindow):
    def __init__(self, qapp, args, variant="rclone_config_gui"):
        super().__init__()
        self.qapp = qapp
        self.variant = variant
        self.args = args
        self.debug = args.debug
        self.min_pw_length = 3
        self.bdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self.prepare_menu()
        self.complete_menu()
        self.create_stausbar()
        self.rclone_control = Rclone_control(args.debug, args.rclone_command)
        self.set_MainWidget()
        #self.create_context_menu()
        self.setWindowIcon(QIcon(os.path.join(self.bdir,'images/favicon.png')))
        self.resize(640, 100)

    def s3_client(self, access_key_id, secret_access_key, endpoint, region_name='ceph'):
        return boto3.client(service_name="s3", aws_access_key_id = access_key_id, aws_secret_access_key = secret_access_key, endpoint_url = 'https://'+endpoint, region_name=region_name)

    def prepare_menu(self):
        self.menu_bar = self.menuBar()
        self.menu = nspace(file=nspace(actions=nspace()), view=nspace(actions=nspace()), help=nspace(actions=nspace()))
        about_text = f"""
        S3 {self.variant} (rclone config GUI) v{__version__}
        (c) 2025 CESNET
        {platform.system()}; {platform.machine()}
        """
        self.menu_str = [
            {
                "label": "&File", "nick": "file",
                "actions": [
                    {"label": "&Open config", "nick": "open",  "shortcut": QKeySequence.Open, "connect": lambda : self.centralWidget()._open_config_dialog()},
                    {"label": "&Exit", "nick": "exit",  "shortcut": QKeySequence.Quit, "connect": lambda : self.centralWidget().quit()},
                ],
            },
            {
                "label": "&Help", "nick": "help",
                "actions": [
                    {"label": "&About", "nick": "about",  "shortcut": None, "connect": lambda : WarningQD(text=about_text).exec()},
                ],
            },
        ]

    def complete_menu(self):
        for mitem in self.menu_str:
            menu = self.menu_bar.addMenu(mitem["label"])
            menu.setMinimumWidth(200)
            for act in mitem["actions"]:
                menu.addAction((action := QAction(act["label"], self)))
                if act["shortcut"] != None: action.setShortcut(act["shortcut"])
                #action.setStatusTip("S3 bucket manager")
                #action.setToolTip("S3 bucket manager")
                action.triggered.connect(act["connect"])
                #act["action"] = action
                setattr(getattr(getattr(self.menu, mitem["nick"]), "actions"), act["nick"], action)
#        print(self.menu)

    def create_stausbar(self):
        self.statusbar = self.statusBar()
        #self.statusbar.addPermanentWidget(QLabel(f"abcd"))
        self.statusbar.showMessage("Ready", 2000)

    def _set_win_title(self, tit=None, state=""):
        if not tit: tit = f"{self.variant} [v{__version__}{f'; state:{state}' if self.debug else ''}]"
        self.setWindowTitle(tit)

    def set_MainWidget(self, data=None):
        self.setCentralWidget(MainWidget(self, self.args, data))
        self.centralWidget().show()

    def set_BotoWidget(self, data=None):
        pass

    def _install_shortcuts(self, widget):
        QShortcut(QKeySequence("Alt+x"), widget, lambda : self.centralWidget().quit())

    def run(self):
        self.show()
        st = self.qapp.exec()
        sys.exit(st)

    def quit(self):
        self.qapp.quit()

