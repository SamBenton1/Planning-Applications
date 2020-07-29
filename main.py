import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from EDDC_QWidget import EDDC_Widget


# noinspection PyArgumentList
class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Planning Application Search")
        self.setMinimumSize(800, 800)
        self.setWindowIcon(QIcon("resources/window_icon.png"))

        # Set Main Widget
        main_widget = QWidget()
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignCenter)

        self.main_display = EDDC_Widget()

        self.layout.addWidget(self.main_display)
        main_widget.setLayout(self.layout)
        self.setCentralWidget(main_widget)


app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec_()
