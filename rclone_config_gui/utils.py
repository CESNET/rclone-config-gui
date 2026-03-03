
import os, sys, base64, secrets
from Crypto.Cipher import AES
from PySide6.QtWidgets import QMessageBox, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QListWidget, QInputDialog
from PySide6.QtGui import QValidator

class WarningQD(QDialog):
    def __init__(self, parent=None, title="About", text="S3 rclone pygui (c) 2025 CESNET", icon=None):
        # icons: QMessageBox.NoIcon QMessageBox.Information QMessageBox.Question QMessageBox.Warning QMessageBox.Critical
        super().__init__(parent)
        self.box = QMessageBox()
        self.box.setWindowTitle(title)
        self.box.setText(text)
        if icon: self.box.setIcon(icon)
        self.box.accepted.connect(self.accept)
        layout = QVBoxLayout()
        layout.addWidget(self.box)
        self.setLayout(layout)

class ConfirmQD(QDialog):
    def __init__(self, parent=None, text="OK?"):
        super().__init__(parent)
        QBtn = ( QDialogButtonBox.Ok | QDialogButtonBox.Cancel )
        self.box = QDialogButtonBox(QBtn)
        self.box.accepted.connect(self.accept)
        self.box.rejected.connect(self.reject)
        layout = QVBoxLayout()
        message = QLabel(text)
        layout.addWidget(message)
        layout.addWidget(self.box)
        self.setLayout(layout)

class InputQD(QInputDialog):
    pass
#    def __init__(self, parent=None):
#        super().__init__(parent)

class SelectQD(QDialog):
    def __init__(self, parent=None, text="OK?", options=[]):
        super().__init__(parent)
        QBtn = ( QDialogButtonBox.Ok | QDialogButtonBox.Cancel )
        self.box = QDialogButtonBox(QBtn)
        self.box.accepted.connect(self.accept)
        self.box.rejected.connect(self.reject)
        layout = QVBoxLayout()
        message = QLabel(text)
        layout.addWidget(message)
        self.list = QListWidget()
        self.list.addItems(options)
        if options: self.list.setCurrentRow(0)
        layout.addWidget(self.list)
        layout.addWidget(self.box)
        self.setLayout(layout)
    def get_selected_option(self):
        return s.text() if (s:=self.list.selectedItems()[0]) else None

class EncProfileValidator(QValidator):
    def __init__(self, edit, profile):
        super().__init__(edit)
        self.edit = edit
        self.profile = profile
    def validate(self, s, p):
        if s!=self.profile.text():
            return QValidator.Acceptable
        else:
            return QValidator.Intermediate

def resource_path(relpath):
    try:
        base = sys._MEIPASS
    except Exception:
        base = os.path.abspath(".")
    return os.path.join(base, relpath)

def rclone_obscure(str, decode=False):
    rc_key = b"\x9c\x93\x5b\x48\x73\x0a\x55\x4d\x6b\xfd\x7c\x63\xc8\x86\xa9\x2b\xd3\x90\x19\x8e\xb8\x12\x8a\xfb\xf4\xde\x16\x2b\x8b\x95\xf6\x38"
    if not decode:
        iv = secrets.token_bytes(AES.block_size)
        aes = AES.new(key=rc_key, mode=AES.MODE_CTR, initial_value=iv, nonce=b'')
        ep = aes.encrypt(str.encode('utf-8'))
        return base64.urlsafe_b64encode(iv + ep).decode('utf-8').rstrip("=")
    else:	# deobscure
        pad = 4 - (len(str) % 4)
        str = str + ("=" * pad)
        str = base64.urlsafe_b64decode(str)
        ep = str[AES.block_size:]
        iv = str[:AES.block_size]
        aes = AES.new(key=rc_key, mode=AES.MODE_CTR, initial_value=iv, nonce=b'')
        dp = aes.decrypt(ep)
        return dp.decode('utf-8')

def rclone_deobscure(str):
    return rclone_obscure(str, True)

def empty_file(filepath):
    with open(filepath, "w"): pass

def fatal_err(msg, status=1):
    print(f"Fatal error: {msg}")
    sys.exit(status)

__all__ = ['WarningQD', 'ConfirmQD', 'SelectQD', 'InputQD', 'resource_path', 'fatal_err', 'rclone_obscure', 'rclone_deobscure', 'empty_file', 'EncProfileValidator']
