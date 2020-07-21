from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import date


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
        self.setDisplayFormat("yyyy-MM-dd")

    def resetIfNotActive(self):
        if not self.active and not self.reset:
            self.setDate(date.today())
            self.active = True

    def eventFilter(self, obj, event):
        if self.calendarWidget() is obj and event.type() == QEvent.Show:
            self.popupSignal.emit()
            self.resetIfNotActive()
        return super(DateEdit, self).eventFilter(obj, event)
