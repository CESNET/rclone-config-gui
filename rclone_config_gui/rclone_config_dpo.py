# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CESNET
#
# rclone_pygui is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

""" rclone config manager for DPO """

import sys, os, json
from PySide6.QtWidgets import QApplication, QGroupBox, QLabel, QLineEdit, QPushButton, QGridLayout, QFileDialog, QMessageBox
from PySide6.QtGui import QAction, QKeySequence, QRegularExpressionValidator
from argparse import ArgumentParser

from .utils import WarningQD, SelectQD, ConfirmQD, rclone_obscure, rclone_deobscure, empty_file
from .anime_player import AnimePlayer, Threaded
from .boto_widget import BotoWidget
from .rclone_pygui_window import MainWindow
from .rclone_pygui_lib import MainWidget, Controller, State
from .mmodel import MModel
from .version import __version__

# ====== MainWindow ==========
class MainWindow4DPO(MainWindow):
    def __init__(self, qapp, args):
        super().__init__(qapp, args, "rclone_config_dpo")

    def prepare_menu(self):
        super().prepare_menu()
        self.menu_str[0]["actions"].insert(0,
            {"label": "&New config", "nick": "new", "shortcut": QKeySequence.New, "connect": lambda : self.centralWidget()._new_config_dialog()}
        )
        self.menu_str.insert(1,
            {
                "label": "&ViewMode", "nick": "view",
                "actions": [
                    {"label": "&Rclone config", "nick": "config",  "shortcut": QKeySequence("Ctrl+r"),
                        "connect": lambda : self.centralWidget()._switch_widgets(self.set_MainWidget)},
                    {"label": "S&3 bucket manager", "nick": "s3",  "shortcut": QKeySequence("Ctrl+3"),
                        "connect": lambda : self.centralWidget()._switch_widgets(self.set_BotoWidget)},
                ],
            }
        )

    def set_MainWidget(self, data=None):
        self.menu.file.actions.new.setEnabled(True)
        self.setCentralWidget(MainWidget4DPO(self, self.args, data, Controller4DPO))
        self.centralWidget().show()

    def set_BotoWidget(self, data=None):
        self.menu.file.actions.new.setEnabled(False)
        try:
            s3 = self.s3_client(data.access_key_id, data.secret_access_key, data.endpoint)
            self.setCentralWidget(BotoWidget(self, self.args, s3, data))
            self.centralWidget().show()
        except Exception as e:
            WarningQD(title="Warning", text=f"{e}", icon=QMessageBox.Warning).exec()
        super().set_BotoWidget(data)

# ====== Controller ==========
class Controller4DPO(Controller):
    def prepare_INIT(self):
        super().prepare_INIT()
        st = self.states[State.INIT]
        menu = self.window.menu
        w = self.widget
        st.assignProperty(menu.file.actions.new, "enabled", True)
        st.assignProperty(menu.view.actions.config, "enabled", False)
        st.assignProperty(menu.view.actions.s3, "enabled", False)
        for it in (w.enc_box, w.gbox_export_pw, w.spinner_export_pw, w.spinner_test_bucket,):
            st.assignProperty(it, "visible", False)
        for it in (w.input_enc_bucket, w.input_export_pw, w.button_export_pw,):
            st.assignProperty(it, "enabled", False)

    def prepare_CONF(self):
        super().prepare_CONF()
        st = self.states[State.CONF]
        menu = self.window.menu
        w = self.widget
        st.assignProperty(menu.view.actions.config, "enabled", False)
        st.assignProperty(menu.view.actions.s3, "enabled", False)
        for it in (w.enc_box, w.gbox_export_pw, w.spinner_export_pw, w.spinner_test_bucket,):
            st.assignProperty(it, "visible", False)
        st.assignProperty(w.button_test_bucket, "icon", w._std_icon("SP_MessageBoxQuestion"))
        for it in (w.input_enc_profile, w.input_enc_bucket, w.input_export_pw, w.button_export_pw,):
            st.assignProperty(it, "enabled", False)

    def prepare_PWOK(self):
        super().prepare_PWOK()
        st = self.states[State.PWOK]
        menu = self.window.menu
        w = self.widget
        st.assignProperty(menu.view.actions.config, "enabled", False)
        st.assignProperty(menu.view.actions.s3, "enabled", True)
        for it in (w.enc_box, w.gbox_export_pw,):
            st.assignProperty(it, "visible", True)
        for it in (w.spinner_export_pw, w.spinner_test_bucket,):
            st.assignProperty(it, "visible", False)
        for it in (w.input_enc_profile, w.input_enc_bucket, w.input_endpoint, w.input_export_pw, w.button_export_pw,):
            st.assignProperty(it, "enabled", True )
        st.assignProperty(w.button_export_pw, "icon", w._std_icon("SP_DialogApplyButton"))

    def do_work_in_PWOK(self):
        super().do_work_in_PWOK()
        st = self.states[State.PWOK]
        if self.widget.data.s3manager_mode == 'return_selected_bucket':
            self.widget.data.enc_bucket = self.widget.data.selected_bucket
            self.widget.data.s3manager_mode = None
        self.widget.data.save_to_widget(self.widget, "enc_vars")
        self.widget.input_endpoint.setFocus()

# ====== MainWidget ==========
class MainWidget4DPO(MainWidget):
    def __init__(self, window, args, data, ctrl_class):
        super().__init__(window, args, data, ctrl_class)
        if self.debug: print("MainWidget4DPO init")

    def prepareGUI(self):
        self.enc_box = self._create_encrypted_profile_box()
        self.gbox_export_pw = self._create_export_box()
        super().prepareGUI()

    def finalizeGUI(self, items=[]):
        items.insert(4, self.enc_box)
        items.append(self.gbox_export_pw)
        self.setTabOrder(self.button_generate_enc_password2, self.input_new_pw)
        self.setTabOrder(self.input_new_pw, self.button_new_pw)
        self.setTabOrder(self.button_new_pw, self.input_export_pw)
        super().finalizeGUI(items)

    def _switch_widgets(self, method=None):
        super()._switch_widgets(method, "all")

    def _new_config_dialog(self):
        selected_config,_ = QFileDialog.getSaveFileName(self, 'Select file name for config ...', '.', "configs (*.conf)")
        if not selected_config: return
        if os.path.isfile(selected_config): empty_file(selected_config)
#        self.window.statusbar.showMessage(f"New config file created: {selected_config}")
        self.data = MModel(self.debug)
        self.set_config_file(selected_config)

    def set_config_file(self, rclconf):
        if not os.path.isfile(rclconf): empty_file(rclconf)
        rclconf = os.path.relpath(rclconf)
        if not os.path.isfile(rclconf):
            self.window.statusbar.showMessage(f"New config file created: {rclconf}")
        super().set_config_file(rclconf)

    def _set_button_test_bucket_state(self, state="?", icon="SP_MessageBoxQuestion"):
        d = {
            "?": {"txt1":"Test Bucket", "txt2":"Test S3 bucket", "icon":"SP_MessageBoxQuestion", "ok":False},
            "ok": {"txt1":"Change Bucket", "txt2":"Change S3 bucket", "icon":"SP_DialogOkButton", "ok":True},
            "no": {"txt1":"Test Bucket", "txt2":"Test S3 bucket", "icon":"SP_MessageBoxCritical", "ok":False},
        }
        self.button_test_bucket.setText(d[state]["txt1"])
        self.button_test_bucket.setToolTip(d[state]["txt2"])
        self._set_button_icon(self.button_test_bucket, d[state]["icon"])
        self.data.bucket_ok = d[state]["ok"]

    def _create_encrypted_profile_box(self):
        gbox = QGroupBox("Encryption-Layer Profile:", parent=self)
        #
#        self.input_enc_profile = QLineEdit("X_enc_profile")
        self.input_profile_name2 = QLineEdit("X_profile")
        self.input_profile_name2.setEnabled(False)
        self.input_enc_bucket = QLineEdit("X-enc-bucket")
        self.input_enc_bucket.setValidator(QRegularExpressionValidator(r"[-a-z0-9]+", self))
        self.button_test_bucket = QPushButton("Test Bucket")
        self._set_button_test_bucket_state("?")
        self.button_test_bucket.clicked.connect(self.process_button_test_bucket)
        self.spinner_test_bucket = AnimePlayer(os.path.join(self.window.bdir,'images/spinner.gif'),parent=self)
        self.spinner_test_bucket.hide()
        self.input_enc_password = QLineEdit("pw")
        self.input_enc_password.setValidator(self.password_validator)
        self.input_enc_password.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.input_enc_password2 = QLineEdit("pw2")
        self.input_enc_password2.setValidator(self.password_validator)
        self.input_enc_password2.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.button_generate_enc_password = QPushButton("Generate")
        self.button_generate_enc_password.setToolTip(f"Generate strong password ({self.rclone_control.pwbits} bits)")
        self.button_generate_enc_password.clicked.connect(lambda : self.input_enc_password.setText(self.rclone_control._generate_pwd()))
        self.button_generate_enc_password2 = QPushButton("Generate")
        self.button_generate_enc_password2.setToolTip(f"Generate strong password ({self.rclone_control.pwbits} bits)")
        self.button_generate_enc_password2.clicked.connect(lambda : self.input_enc_password2.setText(self.rclone_control._generate_pwd()))
        #
        layout = QGridLayout()
        for i, label_text, key, butt, spinner in (
#            (0, "Encryption-layer profile:", "enc_profile", None, None),
            (0, "Underlying S3 profile:", "profile_name2", None, None),
            (1, "Encrypted bucket:", "enc_bucket", self.button_test_bucket, self.spinner_test_bucket),
            (2, "Encryption password:", "enc_password", self.button_generate_enc_password, None),
            (3, "Encryption password2:", "enc_password2", self.button_generate_enc_password2, None),
        ):
            input_widget = getattr(self, f"input_{key}")
            layout.addWidget(QLabel(label_text), i, 0)
            layout.addWidget(input_widget, i, 1, 1, (1+(0 if butt else 1)+(0 if spinner else 1)))
            if spinner: layout.addWidget(spinner, i, 2)
            if butt: layout.addWidget(butt, i, 3)
            input_widget.key = key
            input_widget.textEdited.connect(self._set_edited)
        gbox.setLayout(layout)
        self.gbox_profile_encrypted_config = gbox
        return gbox

    def _create_export_box(self):
        gbox = QGroupBox("Config export for users (w/o S3 credentials):", parent=self)
        #
        self.export_config_label = QLabel("Exported config file: not selected")
        label_export_pw = QLabel("Exported config Password:")
        self.input_export_pw = QLineEdit("", parent=gbox)
        self.input_export_pw.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.input_export_pw.setValidator(self.password_validator)
        self.input_export_pw.setMinimumWidth(240)
        self.input_export_pw.setPlaceholderText("New password for exported config ")
        self.input_export_pw.returnPressed.connect(self.process_button_export_pw)
        #
        self.button_export_pw = QPushButton("Encrypt and export", parent=gbox, disabled=True)
        self.button_export_pw.setToolTip("Export config for users")
        self.button_export_pw.clicked.connect(self.process_button_export_pw)
        #
        self.spinner_export_pw = AnimePlayer(os.path.join(self.window.bdir,'images/spinner.gif'),parent=self)
        #
        layout = QGridLayout()
#        for widget in (self.export_config_label, label_export_pw, self.input_export_pw, self.button_export_pw, self.spinner_export_pw):
#            layout.addWidget(widget)
        layout.addWidget(self.export_config_label, 0, 0, 1, 3)
        layout.addWidget(label_export_pw, 1, 0)
        layout.addWidget(self.input_export_pw, 1, 1)
        layout.addWidget(self.button_export_pw, 1, 2)
        layout.addWidget(self.spinner_export_pw, 1, 3)
        gbox.setLayout(layout)
        return gbox

    def _set_edited(self):
        super()._set_edited()
        sender = self.sender()
        if sender.key == 'enc_bucket' and self.data.bucket_ok:
            self._set_button_test_bucket_state("?")

    def process_button_test_bucket(self):
        bucket = self.input_enc_bucket.text()
        class XThreaded(Threaded):
            def th_init(self):
                self.widget.spinner_test_bucket.show()
            def th_run(self):
                r =  self.widget.window.s3.list_buckets()
                self.buckets = [b['Name'] for b in r['Buckets']]
            def th_finally(self):
                self.widget.spinner_test_bucket.hide()
            def th_ready(self):
                if bucket in self.buckets:
                    bucket_ok = self.widget.data.bucket_ok
                    self.widget._set_button_test_bucket_state("ok")
                    self.widget.window.statusbar.showMessage("OK - bucket exists.", 20000)
                    self.widget.input_enc_bucket.setStyleSheet("QLineEdit {}")
                    if bucket_ok:
                        self.widget.data.s3manager_mode = 'select_bucket'
                        self.widget.ctrl.goPWOKtoBOTO.emit()
                else:
                    self.widget._set_button_test_bucket_state("no")
                    self.widget.window.statusbar.showMessage("Bucket does not exists.", 20000)
                    self.widget.input_enc_bucket.setStyleSheet("QLineEdit {color: '#000'; background-color: '#f44'}")
                    if ConfirmQD(self.widget, "Bucket does not exists - switch to S3 bucket manager?").exec():
                        self.widget.data.s3manager_mode = 'select_bucket'
                        self.widget.ctrl.goPWOKtoBOTO.emit()
                    self.widget.input_enc_bucket.setFocus()
            def th_error(self, errmsg):
                self.widget._set_button_test_bucket_state("no")
                self.widget.window.statusbar.showMessage(errmsg)
        if self._check_fields(('endpoint', 'access_key_id', 'secret_access_key')):
            self.window.s3 = self.window.s3_client(self.input_access_key_id.text(), self.input_secret_access_key.text(), self.input_endpoint.text())
            XThreaded(self)
        else:
            self.window.statusbar.showMessage("Some value is not acceptable.", 10000)

    def process_button_export_pw(self):
        if self.debug: print("process_button_export_pw")
        ok_all = True
        for key in ('enc_password', 'enc_password2', 'export_pw'):
            ok_all &= getattr(self, f"input_{key}").hasAcceptableInput()
        if ok_all: self._new_export_dialog()
        else: self.window.statusbar.showMessage("Some value is not acceptable.", 10000)

    def _new_export_dialog(self):
        export_config,_ = QFileDialog.getSaveFileName(self, 'Select file name for export ...', '.', "configs (*.conf)")
        if not export_config: return
        if os.path.isfile(export_config): empty_file(export_config)
        expconf = os.path.relpath(export_config)
        self.export_config_label.setText(f"Export config File: {expconf}")
        if self.debug: print(f"set_export_file({expconf})")
        # tmp change config to exprot_config in rclone_control:
        self.rclone_control.set_rclone_config(export_config)
        self.export4user()

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
        # select crypt profile if needed:
        if len(s3_profile['crypts'])>1 and (se := SelectQD(text="Select from crypt profiles:", options=[n for n in s3_profile['crypts']])).exec():
            crypt_profile = se.get_selected_option()
        # only one crypt profile
        elif len(s3_profile['crypts'])==1:
            crypt_profile = [n for n in s3_profile['crypts']][0]
        # no crypt profile - create new one:
        else:
            crypt_profile = self._create_enc_profile()
#        self.input_enc_profile.setText(crypt_profile)
        s3_profile['crypts'][crypt_profile]['profile'] = crypt_profile
        if self.debug: print(f"Selected crypt profile: {crypt_profile}")
        crypts = self.data.profiles[profile_name]['crypts']
        crypts[crypt_profile]['bucket'] = crypts[crypt_profile]['remote'].split(':')[1]
        try:
            for key in ('password','password2'):
                if key in crypts[crypt_profile]: crypts[crypt_profile][key] = rclone_deobscure(crypts[crypt_profile][key])
        except ValueError:
            pass
        d = {f"enc_{key}" : (crypts[crypt_profile][key] if key in crypts[crypt_profile] else '') for key in ('profile','bucket','password','password2')}
        self.data.load_from_dict(d)
        if self.data.s3manager_mode == 'return_selected_bucket':
            self.data.s3manager_mode = None
            self.data.enc_bucket = self.data.selected_bucket
            self.data.save_to_widget(self, "all")
        else:
            self.data.save_to_widget(self, "enc_vars")
        return True

    def _create_enc_profile(self):
        self.data.enc_profile = f"{self.data.profile_name}_enc"
        if self.debug: print(f"_create_enc_profile: {self.data.enc_profile=}")
        self.window.statusbar.showMessage(f"No encrypted profile - creating new: {self.data.enc_profile}", 10000)
        self.data.enc_bucket = self.data.template['enc_bucket']
        self.enc_remote = f"{self.data.profile_name}:{self.data.enc_bucket}"
        self.rclone_control.rclone_create_enc_profile(self.input_new_pw.text(), self.data.enc_profile, self.data.enc_bucket, )
        self.data.profiles[self.data.profile_name]['crypts'][self.data.enc_profile] = {
            'remote': self.enc_remote,
        }
        return self.data.enc_profile

    def _set_profile_name(self, profile_name=None):
        super()._set_profile_name(profile_name)
        self.input_profile_name2.setText(profile_name)
        if profile_name != None and profile_name not in self.data.profiles:
            self.data.profiles[profile_name] = {'crypts':{}}
            self._create_enc_profile()
        self.input_enc_profile.setText(self.data.enc_profile)
        self.input_enc_bucket.setText(self.data.enc_bucket)

    def export4user(self):
        class XThreaded(Threaded):
            def th_init(self):
                self.widget.spinner_export_pw.show()
                self.widget.button_export_pw.setEnabled(False)
            def th_run(self):
                self.widget.data.load_from_widget(self.widget)
                n = self.widget.data.get_nspace()
                export_pw = self.widget.input_export_pw.text()
                r = True
                r = r and self.widget.rclone_control.rclone_create_profile(export_pw, self.widget.rclone_control.profile_name, 's3', 'provider=Ceph')
                r = r and self.widget.rclone_control.rclone_change_keys(export_pw, n.endpoint, '', '')
                r = r and self.widget.rclone_control.rclone_create_enc_profile(export_pw, n.enc_profile, n.enc_bucket, n.enc_password, n.enc_password2)
                r = r and self.widget.rclone_control.rclone_change_config_pw(export_pw, export_pw)
                self.widget.status = r
            def th_finally(self):
                self.widget.spinner_export_pw.hide()
                self.widget.button_export_pw.setEnabled(True)
            def th_ready(self):
                if self.widget.debug: print("export_pw_wt_result:", self.widget.status)
                if self.widget.status:
                    if ConfirmQD(self.widget, f"Finished, saved - continue with {self.widget.data.rclone_config}? (or exit)").exec():
#                        self.widget.ctrl.goPWOKtoBOTO.emit()
#                        self.widget.set_config_file(self.widget.data.rclone_config)
                        # restore tmp changed rclone_config in rclone_control:
                        self.widget.rclone_control.set_rclone_config(self.widget.data.rclone_config)
                    else:
                        self.widget.ctrl.goPWOKtoFIN.emit()
            def th_error(self, errmsg):
                WarningQD(title="Warning", text=errmsg, icon=QMessageBox.Warning).exec()
        XThreaded(self)

    def process_button_new_pw(self):
        class XThreaded(Threaded):
            def th_init(self):
                self.widget.spinner_new_pw.show()
                self.widget.button_new_pw.setEnabled(False)
            def th_run(self):
                old_enc_profile = self.widget.data.enc_profile
                self.widget.data.load_from_widget(self.widget)
                n = self.widget.data.get_nspace()
                for key in ('old_pw','new_pw'): setattr(n, key, getattr(self.widget, f"input_{key}").text())
                # run rclone to change config pw:
                if n.new_pw != n.old_pw:
                    self.widget.rclone_control.rclone_change_config_pw(n.old_pw, n.new_pw)
                    self.widget.config_encryption = True
                # run rclone to save S3 keys:
                self.widget.status = self.widget.rclone_control.rclone_change_keys(n.new_pw, n.endpoint, n.access_key_id, n.secret_access_key)
                if not self.widget.status: return
                if n.enc_profile != old_enc_profile:
                    #if ConfirmQD(self.widget, f"Remove existing Encryption-layer Profile \"{old_enc_profile}\"?").exec():
                    r = True
                    r = r and self.widget.rclone_control.rclone_create_enc_profile(n.new_pw, n.enc_profile, n.enc_bucket)
                    r = r and self.widget.rclone_control.rclone_delete_profile(n.new_pw, old_enc_profile)
                    self.widget.status = r
                self.widget.status = self.widget.rclone_control.rclone_configure_enc_profile(n.new_pw, n.enc_profile, n.enc_bucket, n.enc_password, n.enc_password2)
            def th_finally(self):
                self.widget.spinner_new_pw.hide()
                self.widget.button_new_pw.setEnabled(True)
            def th_ready(self):
                if self.widget.debug: print("new_pw_wt_result:", self.widget.status)
                if self.widget.status:
#                    if ConfirmQD(self.widget, "Finished, saved - continue to bucket manager?").exec():
#                        self.widget.ctrl.goPWOKtoBOTO.emit()
                    if ConfirmQD(self.widget, f"Finished, saved - continue with {self.widget.data.rclone_config}?").exec():
                        self.widget.set_config_file(self.widget.data.rclone_config)
                    else:
                        self.widget.ctrl.goPWOKtoFIN.emit()
            def th_error(self, errmsg):
                WarningQD(title="Warning", text=errmsg, icon=QMessageBox.Warning).exec()
        if self._check_fields(('endpoint', 'access_key_id', 'secret_access_key', 'enc_profile', 'enc_bucket', 'enc_password', 'enc_password2', 'new_pw')):
            XThreaded(self)
        else:
            self.window.statusbar.showMessage("Some value is not acceptable.", 10000)

# -----------------------------------------------------------------------------
def parse_args(argv):
    p = ArgumentParser(description="CESNET S3 rclone GUI config for DPO")
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
        match pwchng:
            case "1":
                print(subproc_new_pw)
            case "o":
                print(rclone_obscure(subproc_old_pw))
            case "d":
                print(rclone_deobscure(subproc_old_pw))
            case _:
                print(subproc_old_pw)
    else:
        # normal mode:
        MainWindow4DPO(QApplication(), args).run()

if __name__ == '__main__':
    sys.exit(main())
