
import os.path
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtGui import QMovie
from PySide6.QtCore import QByteArray, QThread, Signal
from .utils import resource_path

class AnimePlayer(QWidget):
    def __init__(self, filename, parent=None):
        QWidget.__init__(self, parent)
        filepath = resource_path(filename)
        if parent.debug and not os.path.isfile(filepath): print(f"File not found: \"{filepath}\"")
        # Load the file into a QMovie
        self.movie = QMovie(filepath, QByteArray(), self)
        self.movie_screen = QLabel()
        # Create the layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.movie_screen)
        self.setLayout(main_layout)
        # Add the QMovie object to the label
        self.movie.setCacheMode(QMovie.CacheAll)
        self.movie.setSpeed(100)
        self.movie_screen.setMovie(self.movie)
        self.movie.start()
    def stop(self):
        self.movie.stop()

class Threaded():
    class WorkerThread(QThread):
        ready, error = Signal(bool), Signal(bool)
        def __init__(self, widget, th=None):
            super().__init__(widget)
            self.th = th
            self.ready.connect(self.process_ready)
            self.error.connect(self.process_error)
            self.finished.connect(self.deleteLater)
        def run(self):
            try:
                self.th.th_run()
                self.ready.emit(True)
            except Exception as e:
                self.errmsg = f"{e}"
                self.error.emit(False)
        def process_ready(self, st):
            self.th.th_finally()
            self.th.th_ready()
        def process_error(self, st):
            self.th.th_finally()
            self.th.th_error(self.errmsg)
    def __init__(self, widget, args={}):
        self.widget, self.args = widget, args
        if False == self.th_init(): return
        Threaded.WorkerThread(widget, self).start()
    def th_init(self):
        pass
    def th_run(self):
        pass
    def th_ready(self):
        pass
        self.th_finally()
    def th_finally(self):
        pass
    def th_error(self, errmsg):
        self.th_finally()
        raise Exception(errmsg)
