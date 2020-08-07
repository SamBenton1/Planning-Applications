from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import date
import json
from issues import Log

# QPushButton
class PanelButton(QPushButton):
    """
    Added event filters for emphasis from shadow when mouse enters the button
    """

    def __init__(self):
        super(PanelButton, self).__init__()
        # PANEL SHADOW
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setColor(QColor("grey"))
        self.shadow.setBlurRadius(8)
        self.shadow.setOffset(5, 5)

        self.setObjectName("panel-button")
        self.setGraphicsEffect(self.shadow)
        self.setMinimumSize(600, 200)

    def enterEvent(self, *args, **kwargs):
        self.shadow.setOffset(8, 8)
        self.shadow.setBlurRadius(11)

    def leaveEvent(self, *args, **kwargs):
        self.shadow.setOffset(5, 5)
        self.shadow.setBlurRadius(8)


# Reimplemented date edit widget to allow for null values
class DateEdit(QDateEdit):
    popupSignal = pyqtSignal()

    def __init__(self, parent=None):
        super(DateEdit, self).__init__(parent)
        self.setCalendarPopup(True)
        self.calendarWidget().installEventFilter(self)
        self.setMinimumDate(QDate(2010, 1, 1))
        self.setSpecialValueText(" ")
        self.setDate(QDate.fromString("01/01/0001", "dd/MM/yyyy"))
        self.active = False
        self.reset = False

    def resetIfNotActive(self):
        if not self.active and not self.reset:
            self.setDate(date.today())
            self.active = True

    def eventFilter(self, obj, event):
        if self.calendarWidget() is obj and event.type() == QEvent.Show:
            self.popupSignal.emit()
            self.resetIfNotActive()
        return super(DateEdit, self).eventFilter(obj, event)


# noinspection PyArgumentList
class SettingsDialog(QDialog):
    def __init__(self):
        super(SettingsDialog, self).__init__()
        self.setWindowIcon(QIcon("resources/window_icon.png"))
        self.setWindowTitle("Settings")
        self.setMinimumSize(200, 100)

        self.simple = False
        self.max_pages = 20

        layout = QGridLayout()

        pages_label = QLabel("Max pages:")
        layout.addWidget(pages_label, 0, 0)
        self.max_pages_spinbox = QSpinBox()
        self.max_pages_spinbox.setValue(self.max_pages)
        self.max_pages_spinbox.setRange(5, 100)
        layout.addWidget(self.max_pages_spinbox, 0, 1)

        simple_label = QLabel("Simple Output:")
        layout.addWidget(simple_label, 1, 0)
        self.simple_checkbox = QCheckBox()
        self.simple_checkbox.setChecked(self.simple)
        layout.addWidget(self.simple_checkbox, 1, 1)

        self.buttons = QDialogButtonBox()
        apply = self.buttons.addButton(QDialogButtonBox.Apply)
        close = self.buttons.addButton(QDialogButtonBox.Close)
        apply.clicked.connect(self.apply)
        close.clicked.connect(self.reject)
        layout.addWidget(self.buttons, 2, 0, 1, 2)

        self.setLayout(layout)

    def apply(self):
        self.simple = bool(self.simple_checkbox.checkState())
        self.max_pages = self.max_pages_spinbox.value()

        with open("settings.json", "w") as settings_file:
            json.dump({
                "max_pages": self.max_pages,
                "simple": self.simple
            }, settings_file, indent=2)

        self.close()

    def change(self):
        with open("settings.json") as settings_file:
            settings_json = json.load(settings_file)
            for key, value in settings_json.items():
                self.__setattr__(key, value)
            self.simple_checkbox.setChecked(self.simple)
            self.max_pages_spinbox.setValue(self.max_pages)

        self.exec_()
