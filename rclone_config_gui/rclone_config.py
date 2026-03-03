#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CESNET
#
# rclone_config_gui is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

""" rclone config manager for users """

import sys, os, json
#from PySide6.QtWidgets import QWidget, QApplication, QGroupBox, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QFormLayout, QStyle, QMainWindow, QFileDialog, QMessageBox
from PySide6.QtWidgets import QApplication, QMessageBox
from argparse import ArgumentParser

from .utils import WarningQD
from .rclone_pygui_window import MainWindow
from .rclone_pygui_lib import MainWidget, Controller
from .version import __version__

# ====== MainWindow ==========
class MainWindow4User(MainWindow):
    def __init__(self, qapp, args):
        super().__init__(qapp, args, "rclone_config_users")

    def set_MainWidget(self, data=None):
        self.setCentralWidget(MainWidget4User(self, self.args, data, Controller4User))
        self.centralWidget().show()

# ====== Controller ==========
class Controller4User(Controller):
    pass

# ====== MainWidget ==========
class MainWidget4User(MainWidget):
    def __init__(self, window, args, data=None, ctrl_class=Controller):
        super().__init__(window, args, data, ctrl_class)
        if self.debug: print("MainWidget4User init")

    def _process_profiles(self):
        ret = super()._process_profiles()
        if not ret: return False
        profile_name = self.data.profile_name
        s3_profile = self.data.profiles[profile_name]
        # looking for crypt profile connected to selected S3 profile:
        for s3p in self.data.profiles:
            s3_profile['crypts'] = {n:p for n,p in self.config_profiles.items() if p['type']=='crypt' and p['remote'].split(':')[0]==profile_name}
            for enc_profile in s3_profile['crypts']: s3_profile['crypts'][enc_profile]['profile'] = enc_profile
        if self.debug: print(json.dumps(self.data.profiles, indent=2))
        if len(s3_profile['crypts'])!=1:
            WarningQD(title="Warning", text=f"Wrong config file\nNone or several encryption-layer profiles\n(count:{len(s3_profile['crypts'])} ... {', '.join(s3_profile['crypts'].keys())})", icon=QMessageBox.Warning).exec()
            self.quit(1)
        crypt_profile = [n for n in s3_profile['crypts']][0]
        self.input_enc_profile.setText(crypt_profile)
        return True

# -----------------------------------------------------------------------------
def parse_args(argv):
    p = ArgumentParser(description="CESNET S3 rclone GUI config for users")
    p.add_argument("-d", "--debug", help="enable debug outputs (default %(default)s)", action="store_true")
    p.add_argument("-c", "--rclone_config", help="rclone config file (default: %(default)s)", default=None)
    p.add_argument("-r", "--rclone_command", help="rclone command, could be full path to command (default: %(default)s)", default='rclone')
    p.add_argument("-p", "--password_command", action="store_true", help="run as rclone password command, for internal use")
    p.add_argument("-v", "--version", action="version", help="print version and exit", version=f"%(prog)s {__version__}")
    return p.parse_args(argv)

def main(argv = None):
    args = parse_args(argv)
    if args.password_command:
        # internal password command mode:
        subproc_old_pw = os.environ.get('PYGUI_RCLONE_OLDPW', "")
        subproc_new_pw = os.environ.get('PYGUI_RCLONE_NEWPW', "")
        pwchng = os.environ.get('RCLONE_PASSWORD_CHANGE', "")
        if pwchng != "1":
            print(subproc_old_pw)
        else:
            print(subproc_new_pw)
    else:
        # normal mode:
        MainWindow4User(QApplication(), args).run()

if __name__ == '__main__':
    sys.exit(main())
