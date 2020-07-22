from PyQt5.QtCore import pyqtSignal, QObject
import PyQt5.QtWidgets
from PyQt5.QtGui import QIcon


# QtSignals for search
class SearchSignals(QObject):
    """
    Contains all the signals sent from the search backend thread to the main GUI
    """
    progress = pyqtSignal(int)
    too_many_results = pyqtSignal(int)
    error = pyqtSignal()
    message = pyqtSignal(str)
    reset = pyqtSignal()
    finished = pyqtSignal(object)


class FileSavedDialog(PyQt5.QtWidgets.QMessageBox):
    def __init__(self):
        super(FileSavedDialog, self).__init__()
        self.setWindowIcon(QIcon(r"resources\window_icon.png"))
        self.setStyleSheet("QLabel{min-width:100 px}")
        self.setIcon(PyQt5.QtWidgets.QMessageBox.Information)
        self.setText("File saved!")
        self.setWindowTitle("Information")
        self.setStandardButtons(PyQt5.QtWidgets.QMessageBox.Ok)
