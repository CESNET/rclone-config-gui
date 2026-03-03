
import os, json
from PySide6.QtWidgets import QWidget, QGroupBox, QLabel, QLineEdit, QPushButton, QVBoxLayout, QFormLayout, QMessageBox, QListWidget, QListWidgetItem
from PySide6.QtGui import QRegularExpressionValidator

from .anime_player import AnimePlayer, Threaded
from .utils import ConfirmQD, WarningQD

class BotoWidget(QWidget):
    def __init__(self, window, args, s3, data=None):
        super().__init__()
        self.debug = args.debug
        self.state = None
        self.window = window
        self.data = data
        self.s3 = s3
        self.buckets = []
        self.bucket = None
        self.prepareGUI()
        self.window._install_shortcuts(self)
        if self.debug: print(f"BotoWidget: Profile: {data.profile_name}")
        self.get_buckets()
        self.data.s3manager_mode = 'return'

    def prepareGUI(self):
        gbox = QGroupBox(f"S3 profile \"{self.data.profile_name}\" on {self.data.endpoint}", parent=self)
        self.spinner_buckets = AnimePlayer(os.path.join(self.window.bdir,'images/spinner.gif'),parent=self)
        self.spinner_buckets.hide()
        self.label_bucket = QLabel(f"Selected bucket: {self.bucket}")
        self.label_buckets = QLabel("Available buckets:")
        self.combo_buckets = QListWidget()
        self.combo_buckets.addItems([])
        self.combo_buckets.setMinimumWidth(400)
        self.combo_buckets.currentItemChanged.connect(self.set_selected_bucket)

        self.input_new_bucket = QLineEdit("")
        self.input_new_bucket.setToolTip("New bucket name")
        self.input_new_bucket.setPlaceholderText("New bucket name")
        self.input_new_bucket.setValidator(QRegularExpressionValidator(r"^[-a-zA-Z0-9._]{1,63}$", self))
        self.input_new_bucket.setMinimumWidth(400)
        self.input_new_bucket.returnPressed.connect(self.create_bucket)
        button_create_bucket = QPushButton("Create bucket")
        button_create_bucket.setMaximumWidth(220)
        button_create_bucket.clicked.connect(self.create_bucket)
        button_delete_bucket = QPushButton("Delete bucket")
        button_delete_bucket.setMaximumWidth(220)
        button_delete_bucket.clicked.connect(self.delete_bucket)
        #button_exit = QPushButton("Exit")
        button_exit = QPushButton("Return")
        button_exit.setMaximumWidth(220)
        #button_exit.clicked.connect(self.quit)
        button_exit.clicked.connect(self.return_back)
        button_select_bucket = QPushButton("Select bucket")
        button_select_bucket.setMaximumWidth(220)
        button_select_bucket.clicked.connect(self.select_bucket)
        layout = QFormLayout()
        for l,r in ((self.input_new_bucket,button_create_bucket), (self.label_bucket,button_delete_bucket),(self.label_buckets,self.spinner_buckets), (self.combo_buckets,None), (None,button_select_bucket), (None,button_exit)):
            if self.data.s3manager_mode=='select_bucket':
                if r!=button_exit: layout.addRow(l,r)
            else:
                if r!=button_select_bucket: layout.addRow(l,r)
        gbox.setLayout(layout)
        win_layout = QVBoxLayout()
        for gbox in (gbox,):
            win_layout.addWidget(gbox)
        self.setLayout(win_layout)
        self.window.menu.file.actions.open.setEnabled(False)
        self.window.menu.view.actions.config.setEnabled(True)
        self.window.menu.view.actions.s3.setEnabled(False)

    def set_selected_bucket(self, bucket=None):
        if isinstance(bucket, QListWidgetItem):
            self.bucket = self.combo_buckets.currentItem().text()
        else:
            self.bucket = bucket
        if self.debug: print(f"itemText: {self.bucket}")
        self.label_bucket.setText(f"Selected bucket: {self.bucket}")

    def get_buckets(self):
        class XThreaded(Threaded):
            def th_init(self):
                self.widget.spinner_buckets.show()
            def th_run(self):
                r =  self.widget.s3.list_buckets()
                self.widget.buckets = [b['Name'] for b in r['Buckets']]
                if self.widget.debug: print(json.dumps(r['Buckets'], indent=2, sort_keys=True, default=str))
            def th_finally(self):
                self.widget.spinner_buckets.hide()
            def th_ready(self):
                if self.widget.debug: print("get_buckets thread ready")
                self.widget.label_buckets.setText("Available buckets:")
                self.widget.combo_buckets.clear()
                self.widget.combo_buckets.addItems(self.widget.buckets)
            def th_error(self, errmsg):
                WarningQD(title="Warning", text=errmsg, icon=QMessageBox.Warning).exec()
        XThreaded(self)

    def create_bucket(self):
        class XThreaded(Threaded):
            def th_init(self):
                self.widget.new_bucket = self.widget.input_new_bucket.text()
                if not isinstance(self.widget.new_bucket, str) or self.widget.new_bucket=="":
                    if self.widget.debug: print(self.widget.new_bucket, type(self.widget.new_bucket))
                    WarningQD(title="Warning", text=f"Wrong bucket name ({self.widget.new_bucket})", icon=QMessageBox.Warning).exec()
                    return False
                if self.widget.debug: print(f"create_bucket \"{self.widget.new_bucket}\"")
                self.widget.spinner_buckets.show()
                self.widget.label_buckets.setText("Creating new bucket ...")
            def th_run(self):
                r =  self.widget.s3.create_bucket(Bucket=self.widget.new_bucket)
                if self.widget.debug: print(r)
            def th_finally(self):
                self.widget.spinner_buckets.hide()
            def th_ready(self):
                self.widget.set_selected_bucket(self.widget.new_bucket)
                self.widget.new_bucket = None
                if self.widget.debug: print("create_bucket thread ready")
                self.widget.input_new_bucket.setText("")
                self.widget.get_buckets()
                self.widget.set_selected_bucket(self.widget.bucket)
            def th_error(self, errmsg):
                WarningQD(title="Warning", text=errmsg, icon=QMessageBox.Warning).exec()
        XThreaded(self)

    def delete_bucket(self):
        class XThreaded(Threaded):
            def th_init(self):
                if not isinstance(self.widget.bucket, str):
                    WarningQD(title="Warning", text="Wrong bucket", icon=QMessageBox.Warning).exec()
                    return False
                if not ConfirmQD(self.widget, f"Really delete bucket \"{self.widget.bucket}\"").exec():
                    if self.widget.debug: print("Cancelled...")
                    return False
                if self.widget.debug: print(f"delete_bucket \"{self.widget.bucket}\"")
                self.widget.spinner_buckets.show()
                self.widget.label_buckets.setText("Deleting bucket ...")
            def th_run(self):
                r =  self.widget.s3.delete_bucket(Bucket=self.widget.bucket)
                if self.widget.debug: print(r)
            def th_finally(self):
                self.widget.spinner_buckets.hide()
            def th_ready(self):
                self.widget.set_selected_bucket()
                if self.widget.debug: print("delete_bucket thread ready")
                self.widget.get_buckets()
                self.widget.set_selected_bucket()
            def th_error(self, errmsg):
                WarningQD(title="Warning", text=errmsg, icon=QMessageBox.Warning).exec()
        XThreaded(self)

    def select_bucket(self):
        if not isinstance(self.bucket, str):
            WarningQD(title="Warning", text="No bucket selected", icon=QMessageBox.Warning).exec()
            return False
        #if self.debug:
        if self.debug: print(f"selected bucket: {self.bucket}")
        self.data.selected_bucket = self.bucket
        self.data.s3manager_mode = 'return_selected_bucket'
        self._switch_widgets(self.window.set_MainWidget)

    def _switch_widgets(self, method=None):
        if self.debug: print("BotoWidget._switch_widgets")
        if method is None: return
        method(self.data)

    def return_back(self):
        self.data.selected_bucket = self.bucket
        self.data.s3manager_mode = 'return'
        self._switch_widgets(self.window.set_MainWidget)

    def quit(self):
        if self.debug: print("Done.")
        self.window.quit()
