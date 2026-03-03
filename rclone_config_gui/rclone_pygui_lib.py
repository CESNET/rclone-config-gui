#
# Copyright (C) 2025 CESNET
#
# rclone_config_gui is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

""" S3 rclone config gui - lib """

import os, json
from PySide6.QtWidgets import QWidget, QGroupBox, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QGridLayout, QStyle, QFileDialog, QMessageBox
from PySide6.QtGui import QRegularExpressionValidator, Qt
from PySide6.QtCore import QObject, Signal
from PySide6.QtStateMachine import QStateMachine, QState, QFinalState
from enum import Enum

from .utils import WarningQD, SelectQD, ConfirmQD, InputQD, EncProfileValidator
from .anime_player import AnimePlayer, Threaded
from .mmodel import MModel

# ====== State ==========
class State(Enum):
    INIT, CONF, PWOK, BOTO, FIN = range(1,6)
    def __str__(self): return f"{self.name}"
    def debug(self): return f"{self.name}[{self.value}]"
    @classmethod
    def start_state(cls): return cls.INIT
    @classmethod
    def finish_state(cls): return cls.FIN
    @classmethod
    def states(cls): return [s for s in (cls)]
    @classmethod
    def regular_states(cls): return [s for s in (cls) if s != cls.finish_state()]
    @classmethod
    def transitions(cls):
        """ Signals with name f"go{src_state}to{dst_state}" have to be declared in Controller """
        return {
            cls.INIT: [ cls.CONF ],
            cls.CONF: [ cls.CONF, cls.PWOK ],
            cls.PWOK: [ cls.CONF, cls.BOTO, cls.FIN ],
            cls.BOTO: [ cls.CONF, cls.FIN ],
        }

# ====== Controller ==========
class Controller(QObject):
    """ Object with Signals for transition processing."""
    goINITtoCONF = Signal()
    goCONFtoCONF = Signal()
    goCONFtoPWOK = Signal()
    goPWOKtoCONF = Signal()
    goPWOKtoBOTO = Signal()
    goPWOKtoFIN = Signal()
    goBOTOtoCONF = Signal()
    goBOTOtoFIN = Signal()

    def __init__(self, widget, rcl):
        super().__init__()
        self.widget = widget
        self.rclone_control = rcl
#        self.states = widget.states
        self.window = widget.window
        self.states = {}
        for s in State.regular_states(): self.states[s] = QState()
        self.states[State.finish_state()] = QFinalState()
        for s in State.states():
            if (meth:=f"do_work_in_{s}") not in dir(self):
                setattr(self, meth, lambda s=s: print(f"work in {s}"))
        # --- Signal to transition binding ---
        for src, dsts in State.transitions().items():
            for dst in dsts:
                self.states[src].addTransition(getattr(self,f"go{src}to{dst}"), self.states[dst])
        # --- state-entered handlers ---
        for s in State.states(): self.states[s].entered.connect(lambda s=s: self.widget._entered_state(s))
        for s in State.states(): self.states[s].entered.connect(lambda s=s: getattr(self, f"do_work_in_{s}")())
        # --- state-exited handlers ---
        self.states[State.finish_state()].exited.connect(lambda : print(f"exited {State.finish_state()}"))

    # --- INIT ----------
    def prepare_INIT(self):
        st = self.states[State.INIT]
        menu = self.window.menu
        w = self.widget
        st.assignProperty(menu.file.actions.open, "enabled", True)
        for it in (
            w.gbox_old_pw, w.gbox_profile_config, w.gbox_new_pw,
            w.spinner_old_pw, w.spinner_new_pw, w.spinner_test_s3
        ):
            st.assignProperty(it, "visible", False)
        for key in ('profile_name', 'endpoint', 'access_key_id', 'secret_access_key'):
            st.assignProperty(getattr(w, f"input_{key}"), "enabled", False)
            st.assignProperty(getattr(w, f"input_{key}"), "text", "")
        for it in (w.input_new_pw, w.button_new_pw, ):
            st.assignProperty(it, "enabled", False)
        for it in (w.button_old_pw, w.button_new_pw,):
            st.assignProperty(it, "icon", w._std_icon("SP_DialogCloseButton"))

    def do_work_in_INIT(self):
        if self.widget.debug: print("work in INIT (METHOD)")
        rclconf = None
        if self.widget.data.rclone_config != None:
            rclconf = self.widget.data.rclone_config
        else:
            if self.window.args.rclone_config != None:
                rclconf = self.window.args.rclone_config
        if rclconf != None: self.widget.set_config_file(rclconf)

    # --- CONF ----------
    def prepare_CONF(self):
        st = self.states[State.CONF]
        menu = self.window.menu
        w = self.widget
        st.assignProperty(menu.file.actions.open, "enabled", True)
        for it in (
            w.gbox_profile_config, w.gbox_new_pw,
            w.spinner_old_pw, w.spinner_new_pw, w.spinner_test_s3
        ):
            st.assignProperty(it, "visible", False)
        st.assignProperty(w.gbox_old_pw, "visible", True)
        for key in ('profile_name', 'endpoint', 'access_key_id', 'secret_access_key'):
            st.assignProperty(getattr(w, f"input_{key}"), "enabled", False)
            st.assignProperty(getattr(w, f"input_{key}"), "text", getattr(w.data, f"{key}"))
        for it in (w.input_old_pw, w.button_old_pw,):
            st.assignProperty(it, "enabled", True)
        st.assignProperty(w.input_old_pw, "text", "")
        st.assignProperty(w.button_old_pw, "icon", w._std_icon("SP_DialogOpenButton"))
        st.assignProperty(w.button_test_s3, "icon", w._std_icon("SP_MessageBoxQuestion"))
        st.assignProperty(w.button_new_pw, "icon", w._std_icon("SP_DialogCloseButton"))

    def do_work_in_CONF(self):
        if self.widget.debug: print("work in CONF (METHOD)")
        if self.widget.data.s3manager_mode != None:
            self.goCONFtoPWOK.emit()
            return
        self.widget.process_config_encryption_status()
        self.widget._set_profile_name()
        self.widget.data.load_from_dict({'endpoint':'', 'access_key_id':'', 'secret_access_key':''})
        self.widget.data.save_to_widget(self.widget, "s3_vars")
        self.widget.input_old_pw.setFocus()

    # --- PWOK ----------
    def prepare_PWOK(self):
        st = self.states[State.PWOK]
        menu = self.window.menu
        w = self.widget
        st.assignProperty(menu.file.actions.open, "enabled", True)
        for it in (w.gbox_old_pw, w.gbox_profile_config, w.gbox_new_pw):
            st.assignProperty(it, "visible", True)
        for it in (w.spinner_old_pw, w.spinner_new_pw, w.spinner_test_s3):
            st.assignProperty(it, "visible", False)
        for it in (w.input_old_pw, w.button_old_pw,):
            st.assignProperty(it, "enabled", False)
        for it in (w.input_new_pw, w.button_new_pw):
            st.assignProperty(it, "enabled", True)
        for key in ('profile_name', 'endpoint', 'access_key_id', 'secret_access_key'):
            st.assignProperty(getattr(w, f"input_{key}"), "enabled", key not in ('profile_name','endpoint'))
            st.assignProperty(getattr(w, f"input_{key}"), "text", getattr(w.data, f"{key}"))
        st.assignProperty(w.input_new_pw, "text", "")
        st.assignProperty(w.button_old_pw, "icon", w._std_icon("SP_DialogOkButton"))
        st.assignProperty(w.button_new_pw, "icon", w._std_icon("SP_DialogApplyButton"))

    def do_work_in_PWOK(self):
        if self.widget.debug: print("work in PWOK (METHOD)")
        self.widget._set_profile_name(self.widget.data.profile_name)
        self.widget.data.save_to_widget(self.widget, "s3_vars")
        self.widget.input_access_key_id.setFocus()

    # --- BOTO ----------
    def prepare_BOTO(self):
        pass
    def do_work_in_BOTO(self):
        if self.widget.debug: print("work in BOTO (METHOD)")
        self.widget._switch_widgets(self.widget.window.set_BotoWidget)
    # --- FIN ----------
    def prepare_FIN(self):
        pass
    def do_work_in_FIN(self):
        if self.widget.debug: print("work in FIN (METHOD)")
        self.widget.quit()

# ====== MainWidget ==========
class MainWidget(QWidget):
    def __init__(self, window, args, data=None, ctrl_class=Controller):
        super().__init__()
        self.debug = args.debug
        self.data = MModel(self.debug) if data is None else data
        self.window = window
        self.rclone_control = self.window.rclone_control
        self.window._install_shortcuts(self)
        self.password_validator = QRegularExpressionValidator(rf".{{{self.window.min_pw_length},}}", self)
        self.prepareGUI()
        self.ctrl = ctrl_class(self, self.rclone_control)
        self._state_machine()

    def _dbg(self):
        c = self.machine.configuration()
        if len(c)!=1: print(f"stmachine conf.: ({c})")
        for s in State.states():
            if self.states[s] in c: print(f"aktual state: {s}")

    def _entered_state(self, new_state):
        self.state = new_state
        self.window._set_win_title(None, self.state)
        if self.debug: print(f"entered state {new_state}")

    def _state_machine(self):
        self.machine = QStateMachine()
        self.states = self.ctrl.states
        # --- call prepare_{state} metohds - assignProperties on enter to states ---
        for s in State.regular_states(): getattr(self.ctrl, f"prepare_{s}")()
        #
        # --- Adding states to statemachine ---
        for s in State.states(): self.machine.addState(self.states[s])
        self.machine.setInitialState(self.states[State.start_state()])
        #
        if self.debug: self.machine.finished.connect(lambda: print("Machine finished"))
        self.machine.start()
        if self.debug: print("st.machine started ...")

    def set_config_file(self, rclconf):
        rclconf = os.path.relpath(rclconf)
        self.data.set_config_file(rclconf)
        self.rclone_control.set_rclone_config(rclconf)
        self.rclone_config_label.setText(f"Config File: {rclconf}")
        getattr(self.ctrl, f"go{self.state}toCONF").emit()

    def prepareGUI(self):
        ver = f"({self.rclone_control.rclone_version})" if self.rclone_control.rclone_version else ''
        self.rclone_label = QLabel(f"Rclone Command: {self.rclone_control.rclone_command} {ver}")
        self.rclone_config_label = QLabel(f"Config File: {self.rclone_control.get_rclone_config()}")
        self.gbox_old_pw = self._create_old_password_box()
        self.gbox_profile_config = self._create_profile_config_box()
        self.gbox_new_pw = self._create_new_password_box()
        items = [self.rclone_label, self.rclone_config_label, self.gbox_old_pw, self.gbox_profile_config, self.gbox_new_pw]
        self.finalizeGUI(items)

    def finalizeGUI(self, items=[]):
        self.win_layout = QVBoxLayout()
        self.win_layout.setAlignment(Qt.AlignTop)
        for gbox in items:
            self.win_layout.addWidget(gbox)
        self.setLayout(self.win_layout)

    def _open_config_dialog(self):
        selected_config,_ = QFileDialog.getOpenFileName(self, 'Select rclone config ...', '.', "configs (*.conf)")
        if not selected_config: return
        if self.debug: print(f"Selected config file: {selected_config}")
        self.data = MModel(self.debug)
        self.set_config_file(selected_config)

    def _switch_widgets(self, method=None, vars="s3_vars"):
        if self.debug: print("MainWidget._switch_widgets")
        if method is None: return
        self.data.load_from_widget(self, vars)
        method(self.data)

    def _create_old_password_box(self):
        gbox = QGroupBox("Config encrypted, input password:", parent=self)
        #
        label = QLabel("Password:")
        self.input_old_pw = QLineEdit("", parent=gbox)
        self.input_old_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_old_pw.setMinimumWidth(240)
        self.input_old_pw.setPlaceholderText("Enter config password")
        self.input_old_pw.returnPressed.connect(self.process_button_old_pw)
        #
        self.button_old_pw = QPushButton("Decrypt to memory", parent=gbox)
        self.button_old_pw.setToolTip("Check password and read config")
        self.button_old_pw.clicked.connect(self.process_button_old_pw)
        #
        self.spinner_old_pw = AnimePlayer(os.path.join(self.window.bdir,'images/spinner.gif'),parent=self)
        layout = QHBoxLayout()
        for widget in (label, self.input_old_pw, self.button_old_pw, self.spinner_old_pw):
            layout.addWidget(widget)
        gbox.setLayout(layout)
        return gbox

    def _set_edited(self):
        sender = self.sender()
        dataval = getattr(self.data, sender.key)
        same = (sender.text() == dataval)
        if not same: self.data.edited.add(sender.key)
        elif sender.key in self.data.edited: self.data.edited.remove(sender.key)
        style = None
        if not same: style = "color: '#f00'"
        if not sender.hasAcceptableInput(): style = "color: '#000'; background-color: '#f44'"
        sender.setStyleSheet(f"QLineEdit {{{style}}}" if style else "")

    def _create_profile_config_box(self):
        gbox = QGroupBox("S3 confguration:", parent=self)
        #
        self.input_profile_name = QLineEdit('not selected')
        self.input_profile_name.setEnabled(False)
        self.input_profile_name.setValidator(QRegularExpressionValidator(r"[-_a-zA-Z0-9]+", self))
        self.input_enc_profile = QLineEdit('')
        self.input_enc_profile.setEnabled(False)
        self.input_enc_profile.setValidator(EncProfileValidator(self,self.input_profile_name))
        self.input_endpoint = QLineEdit(self.data.endpoint)
        self.input_endpoint.setValidator(QRegularExpressionValidator(r"[a-z0-9\.]+", self))
        self.input_access_key_id = QLineEdit(self.data.access_key_id)
        self.input_access_key_id.setValidator(QRegularExpressionValidator(r"[a-zA-Z0-9]+", self))
        self.input_secret_access_key = QLineEdit(self.data.secret_access_key)
        self.input_secret_access_key.setValidator(QRegularExpressionValidator(r"[a-zA-Z0-9]+", self))
        self.input_secret_access_key.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.button_test_s3 = QPushButton("Test S3")
        self.button_test_s3.setToolTip("Test S3 configuration")
        self.button_test_s3.clicked.connect(self.process_button_test_s3)
        self.spinner_test_s3 = AnimePlayer(os.path.join(self.window.bdir,'images/spinner.gif'),parent=self)
        self.spinner_test_s3.hide()
        #
        layout = QGridLayout()
        for i, label_text, key, butt, spinner in (
            (0, "S3 Profile:", "profile_name", None, None),
            (1, "Encryption-layer profile:", "enc_profile", None, None),
            (2, "S3 Endpoint:", "endpoint", None, None),
            (3, "Access Key Id:", "access_key_id", None, None),
            (4, "Secret Access Key:", "secret_access_key", self.button_test_s3, self.spinner_test_s3),
        ):
            input_widget = getattr(self, f"input_{key}")
            layout.addWidget(QLabel(label_text), i, 0)
            layout.addWidget(input_widget, i, 1, 1, (1+(0 if butt else 1)+(0 if spinner else 1)))
            if spinner: layout.addWidget(spinner, i, 2)
            if butt: layout.addWidget(butt, i, 3)
            input_widget.key = key
            input_widget.textEdited.connect(self._set_edited)
        gbox.setLayout(layout)
        self.gbox_profile_config = gbox
        return gbox

    def _create_new_password_box(self):
        gbox = QGroupBox("Config encrypt password:", parent=self)
        #
        label = QLabel("New config password:")
        self.input_new_pw = QLineEdit("", parent=gbox)
        self.input_new_pw.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.input_new_pw.setValidator(self.password_validator)
        self.input_new_pw.setMinimumWidth(240)
        self.input_new_pw.setPlaceholderText("New config password")
        self.input_new_pw.returnPressed.connect(self.process_button_new_pw)
        #
        self.button_new_pw = QPushButton("Save encrypted", parent=gbox, disabled=True)
        self.button_new_pw.setToolTip("Save keys and set new password")
        self.button_new_pw.clicked.connect(self.process_button_new_pw)
        #
        self.spinner_new_pw = AnimePlayer(os.path.join(self.window.bdir,'images/spinner.gif'),parent=self)
        #
        layout = QHBoxLayout()
        for widget in (label, self.input_new_pw, self.button_new_pw, self.spinner_new_pw):
            layout.addWidget(widget)
        gbox.setLayout(layout)
        return gbox

    def _std_icon(self, icon_name):
        return self.style().standardIcon(getattr(QStyle, icon_name))
    def _set_button_icon(self, button, icon_name):
        button.setIcon(self._std_icon(icon_name))

    def process_button_test_s3(self):
        class XThreaded(Threaded):
            def th_init(self):
                self.widget.spinner_test_s3.show()
            def th_run(self):
                self.widget.window.s3.list_buckets()
            def th_finally(self):
                self.widget.spinner_test_s3.hide()
            def th_ready(self):
                self.widget._set_button_icon(self.widget.button_test_s3, "SP_DialogOkButton")
                self.widget.window.statusbar.showMessage("Valid S3 confgiguration.", 20000)
            def th_error(self, errmsg):
                self.widget._set_button_icon(self.widget.button_test_s3, "SP_MessageBoxCritical")
                self.widget.window.statusbar.showMessage(errmsg)
        if self._check_fields(('endpoint', 'access_key_id', 'secret_access_key')):
            self.window.s3 = self.window.s3_client(self.input_access_key_id.text(), self.input_secret_access_key.text(), self.input_endpoint.text())
            XThreaded(self)
        else:
            self.window.statusbar.showMessage("Some value is not acceptable.", 10000)

    def _process_profiles(self):
        s3_profiles = self.data.profiles = {n:p for n,p in self.config_profiles.items() if p['type']=='s3'}
        if self.debug: print(json.dumps(s3_profiles, indent=2))
        # select s3 profile if needed:
        if len(s3_profiles)>1 and (s := SelectQD(text="Select from S3 profiles:", options=[n for n in s3_profiles])).exec():
            profile_name = s.get_selected_option()
        elif len(s3_profiles)==1:
            profile_name = [n for n in s3_profiles.keys()][0]
        else:
            return False
        if self.debug: print(f"Selected profile {profile_name=}")
        self._set_profile_name(profile_name)
#        self.data.profile = s3_profiles[profile_name]
#        self.data.profile['profile_name'] = self.data.profile_name = profile_name
        self.data.profiles[profile_name]['profile_name'] = profile_name
        self.data.load_from_dict(s3_profiles[profile_name])
        return True

    def call_config_check(self, passwd, callback):
        class XThreaded(Threaded):
            def th_init(self):
                self.widget.spinner_old_pw.show()
                self.widget.button_old_pw.setEnabled(False)
                self.widget._set_button_icon(self.widget.button_old_pw, 'SP_DialogCloseButton')
            def th_run(self):
                self.widget.check, self.widget.config_profiles = self.widget.rclone_control.rclone_config_check(self.args['passwd'])
            def th_finally(self):
                self.widget.spinner_old_pw.hide()
                self.widget.button_old_pw.setEnabled(True)
                self.widget._set_button_icon(self.widget.button_old_pw, 'SP_DialogOpenButton')
            def th_ready(self):
                if self.widget.debug: print("check_result:", self.widget.check)
                self.args['callback'](True, self.widget.check)
            def th_error(self, errmsg):
                self.args['callback'](False, None, errmsg)
        XThreaded(self, args={'passwd':passwd, 'callback':callback})

    def process_button_old_pw(self):
        def get_result(status, result, errmsg=''):
            if self.debug: print(f"process_button_old_pw:get_result: {status=}; {result=}; {errmsg=}")
            if not status:
                WarningQD(title="Warning", text=errmsg, icon=QMessageBox.Warning).exec()
                return
            if not self.check:
                WarningQD(title="Warning", text="Password check failed", icon=QMessageBox.Warning).exec()
                self.data.rclone_config_pw = None
                self.ctrl.goINITtoCONF.emit()
                return
            if not self._process_profiles():
                #WarningQD(title="Warning", text="No S3 profile in config", icon=QMessageBox.Warning).exec()
#                if ConfirmQD(text="No S3 profile in config - create new?").exec():
                profile_name, ok = InputQD.getText(self, "InputDialog: Profile Name", "No S3 profile in config - enter new name for profile to be created:"+" "*40)
                if ok:
#                    self._set_profile_name(profile_name,)
                    self.data.profile_name = profile_name
                    self.rclone_control.rclone_create_profile('', profile_name, 's3', 'provider=Ceph')
#                    self.set_config_file(self.rclone_control.get_rclone_config())
#                return
            self.ctrl.goCONFtoPWOK.emit()
        self.data.rclone_config_pw = self.input_old_pw.text()
        self.call_config_check(self.data.rclone_config_pw, get_result)

    def process_config_encryption_status(self):
        def get_result(status, result, errmsg=''):
            if self.debug: print(f"process_config_encryption_status:get_result: {status=}; {result=}; {self.check=}; {errmsg=}")
            if status:
                self.rclone_control.config_encrypted = not (self.check and (self.data.rclone_config_pw == None))
                if not self.rclone_control.config_encrypted:
                    self.gbox_old_pw.setTitle("Config not encrypted")
                    self.data.rclone_config_pw = None
                    self.process_button_old_pw()
                elif self.data.rclone_config_pw != None:
                    self.input_old_pw.setText(self.data.rclone_config_pw)
                    self.process_button_old_pw()
                else:
                    self.gbox_old_pw.setTitle("Config encrypted, input password:")
            else:
                WarningQD(title="Warning", text=errmsg, icon=QMessageBox.Warning).exec()
        pw = self.data.rclone_config_pw
        if pw == None: pw = ''
        self.call_config_check(pw, get_result)

    def process_button_new_pw(self):
        class XThreaded(Threaded):
            def th_init(self):
                self.widget.spinner_new_pw.show()
                self.widget.button_new_pw.setEnabled(False)
            def th_run(self):
                self.widget.data.load_from_widget(self.widget, "s3_vars")
                n = self.widget.data.get_nspace()
                for key in ('old_pw','new_pw'): setattr(n, key, getattr(self.widget, f"input_{key}").text())
                # run rclone to change config pw:
                if n.new_pw != n.old_pw:
                    self.widget.rclone_control.rclone_change_config_pw(n.old_pw, n.new_pw)
                    self.widget.config_encryption = True
                # run rclone to save S3 keys:
                self.widget.status = self.widget.rclone_control.rclone_change_keys(n.new_pw, n.endpoint, n.access_key_id, n.secret_access_key)
            def th_finally(self):
                self.widget.spinner_new_pw.hide()
                self.widget.button_new_pw.setEnabled(True)
            def th_ready(self):
                if self.widget.debug: print("new_pw_wt_result:", self.widget.status)
                if self.widget.status:
                    if ConfirmQD(self.widget, "Finished, saved - exit?").exec():
                        self.widget.ctrl.goPWOKtoFIN.emit()
            def th_error(self, errmsg):
                WarningQD(title="Warning", text=errmsg, icon=QMessageBox.Warning).exec()
        if self._check_fields(('endpoint', 'access_key_id', 'secret_access_key', 'new_pw')):
            XThreaded(self)
        else:
            self.window.statusbar.showMessage("Some value is not acceptable.", 10000)

    def _set_profile_name(self, profile_name=None):
        if self.debug: print(f"_set_profile_name: {profile_name=}")
        self.data.profile_name = profile_name
        self.rclone_control.profile_name = profile_name
        self.input_profile_name.setText(profile_name if profile_name!=None else 'not selected')

    def _check_fields(self, keys):
        ok_all = True
        for key in keys:
            ok = (edit := getattr(self, f"input_{key}")).hasAcceptableInput()
            ok_all &= ok
            if not ok:
                style = "color: '#000'; background-color: '#f44'"
                edit.setStyleSheet(f"QLineEdit {{{style}}}")
        return ok_all

    def quit(self):
        if self.debug: print("Done.")
        self.window.quit()
