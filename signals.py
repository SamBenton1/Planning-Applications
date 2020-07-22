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


# DIALOG BOXES

class FileSavedDialog(PyQt5.QtWidgets.QMessageBox):
    def __init__(self):
        super(FileSavedDialog, self).__init__()
        self.setWindowIcon(QIcon(r"resources\window_icon.png"))
        self.setStyleSheet("QLabel{min-width:100 px}")
        self.setIcon(PyQt5.QtWidgets.QMessageBox.Information)
        self.setText("File saved!")
        self.setWindowTitle("Information")
        self.setStandardButtons(PyQt5.QtWidgets.QMessageBox.Ok)


class TooManyResultsDialog(PyQt5.QtWidgets.QMessageBox):
    def __init__(self, number):
        super(TooManyResultsDialog, self).__init__()
        self.setWindowIcon(QIcon("resources/window_icon.png"))
        self.setIcon(PyQt5.QtWidgets.QMessageBox.Warning)
        self.setText(
            f"The search returned {number} pages of results. This exceeds the limit for the number"
            f" of pages of results. To turn off this limit go to settings.")
        self.setStandardButtons(PyQt5.QtWidgets.QMessageBox.Ok)
        self.setWindowTitle("Warning")
