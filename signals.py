from PyQt5.QtCore import pyqtSignal, QObject


# QtSingals for search
class SearchSignals(QObject):
    """
    Contains all the signals sent from the search backend thread to the main GUI
    """
    progress = pyqtSignal(int)
    too_many_results = pyqtSignal(int)
    error = pyqtSignal()
    message = pyqtSignal(str)