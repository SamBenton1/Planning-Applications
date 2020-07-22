import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from QtReimplementations import PanelButton
from EDDC_QWidget import EDDC_Widget
from Poole_QWidget import Poole_Widget

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

        # Which Search you are in
        self.current_view = 0

        self.main_display = MainDisplay()
        self.main_display.east_search.clicked.connect(self.GotoEDDC)
        self.main_display.poole_search.clicked.connect(self.GotoPoole)

        self.eddc_search = EDDC_Widget()
        self.eddc_search.back_button.clicked.connect(self.GotoHome)
        self.poole_search = Poole_Widget()
        self.poole_search.back_button.clicked.connect(self.GotoHome)

        self.layout.addWidget(self.main_display)
        main_widget.setLayout(self.layout)
        self.setCentralWidget(main_widget)

    def GotoEDDC(self):
        self.main_display.setParent(None)
        self.layout.addWidget(self.eddc_search)

    def GotoPoole(self):
        self.main_display.setParent(None)
        self.layout.addWidget(self.poole_search)

    def GotoHome(self):
        self.poole_search.setParent(None)
        self.eddc_search.setParent(None)
        self.layout.addWidget(self.main_display)


# noinspection PyArgumentList
class MainDisplay(QWidget):
    stylesheet = open("resources/home.css", "r").read()

    def __init__(self):
        super(MainDisplay, self).__init__()

        self.setStyleSheet(self.stylesheet)

        self.setObjectName("inner-widget")

        layout = QVBoxLayout()
        layout.setSpacing(30)

        title = QLabel("Select a website to\nuse for your search...")
        title.setObjectName("title")
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setColor(QColor("grey"))
        self.shadow.setBlurRadius(8)
        self.shadow.setOffset(5, 5)
        title.setGraphicsEffect(self.shadow)
        layout.addWidget(title, alignment=Qt.AlignCenter)

        # POOLE
        self.poole_search = PanelButton()
        poole_layout = QGridLayout()
        poole_layout.setContentsMargins(20, 20, 20, 20)
        self.poole_search.setLayout(poole_layout)

        # Icon
        poole_icon = QLabel()
        poole_icon.setPixmap(QPixmap("resources/Poole_icon.png"))
        poole_icon.setScaledContents(True)
        poole_icon.setFixedSize(160, 160)
        poole_layout.addWidget(poole_icon, 0, 0)

        # Label
        poole_label = QLabel("Poole Planning \nApplication Search")
        poole_label.setObjectName("panel-title")
        poole_label.setAlignment(Qt.AlignCenter)
        poole_layout.addWidget(poole_label, 0, 1)

        # EDDC
        self.east_search = PanelButton()
        east_dorset_layout = QGridLayout()
        east_dorset_layout.setContentsMargins(20, 20, 20, 20)
        self.east_search.setLayout(east_dorset_layout)

        # Icon
        east_dorset_icon = QLabel()
        east_dorset_icon.setPixmap(QPixmap("resources/EDDC_icon.PNG"))
        east_dorset_icon.setScaledContents(True)
        east_dorset_icon.setFixedSize(200, 100)
        east_dorset_layout.addWidget(east_dorset_icon, 0, 0)

        # Label
        east_label = QLabel("East Dorset Planning \nApplication Search")
        east_label.setObjectName("panel-title")
        east_label.setAlignment(Qt.AlignCenter)
        east_dorset_layout.addWidget(east_label, 0, 1)

        layout.addWidget(self.poole_search)
        layout.addWidget(self.east_search)

        self.setLayout(layout)


app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec_()
