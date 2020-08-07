import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5 import QtCore
from QtReimplementations import DateEdit, SettingsDialog
from select_reference import *
import EDDC_search
from signals import FileSavedDialog, TooManyResultsDialog
import os


# noinspection PyArgumentList
class MainWindow(QMainWindow):
    stylesheet = open("resources/EDDC.css").read()
    continue_search = QtCore.pyqtSignal(bool)

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Planning Application Search")
        self.setMinimumSize(800, 800)
        self.setWindowIcon(QIcon("resources/window_icon.png"))

        self.thread_pool = QtCore.QThreadPool()

        # Style
        self.setStyleSheet(self.stylesheet)

        # Main Widget
        main_widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignHCenter)

        # MenuBar
        self.settings = SettingsDialog()

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(lambda: self.settings.change())

        menu = self.menuBar()
        menu.setLayoutDirection(QtCore.Qt.RightToLeft)
        menu.addAction(settings_action)

        # Scroll Area
        scroll_area = QScrollArea()
        scroll_area.setMaximumWidth(850)
        scroll_area.setMaximumHeight(900)
        scroll_area.setWidgetResizable(True)
        scroll_area_contents = QWidget()
        scroll_area_contents.setObjectName("scroll-area")
        self.scroll_area_contents_layout = QGridLayout()
        self.scroll_area_contents_layout.setContentsMargins(30, 10, 30, 10)
        self.scroll_area_contents_layout.setSpacing(10)

        # ------------------- START SCROLL -----------------------------

        title = QLabel("Advanced Search - East Dorset")
        title.setObjectName("title")
        self.scroll_area_contents_layout.addWidget(title, 0, 1, alignment=QtCore.Qt.AlignCenter)

        east_dorset_icon = QLabel()
        east_dorset_icon.setPixmap(QPixmap("resources/EDDC_icon.PNG"))
        east_dorset_icon.setScaledContents(True)
        east_dorset_icon.setObjectName("icon")
        east_dorset_icon.setFixedSize(175, 75)
        self.scroll_area_contents_layout.addWidget(east_dorset_icon, 0, 0)

        # BOX 1
        box_one = QWidget()
        box_one.setObjectName("content-box")

        box_one_layout = QGridLayout()
        box_one.setLayout(box_one_layout)

        box_one_layout.addWidget(QLabel("View outstanding applications only:"), 0, 0)
        self.outstanding_only = QCheckBox()
        box_one_layout.addWidget(self.outstanding_only, 0, 1)

        box_one_layout.addWidget(QLabel("Application Number:"), 1, 0)
        self.application_number = QLineEdit()
        box_one_layout.addWidget(self.application_number, 1, 1)

        box_one_layout.addWidget(QLabel("Address:"), 2, 0)
        self.address = QLineEdit()
        box_one_layout.addWidget(self.address, 2, 1)

        box_one_layout.addWidget(QLabel("Proposal:"), 3, 0)
        self.proposal = QLineEdit()
        box_one_layout.addWidget(self.proposal, 3, 1)

        box_one_layout.addWidget(QLabel("Agent's name:"), 4, 0)
        self.agents_name = QLineEdit()
        box_one_layout.addWidget(self.agents_name, 4, 1)

        box_one_layout.addWidget(QLabel("Parish:"), 5, 0)
        self.parish = QComboBox()
        self.parish.addItems(list(EDDC_PARISH.keys()))
        box_one_layout.addWidget(self.parish, 5, 1)

        box_one_layout.addWidget(QLabel("Ward:"), 6, 0)
        self.ward = QComboBox()
        self.ward.addItems(list(EDDC_WARD.keys()))
        box_one_layout.addWidget(self.ward, 6, 1)

        self.scroll_area_contents_layout.addWidget(box_one, 1, 0, 1, 2)

        # BOX 2
        box_two = QWidget()
        box_two.setObjectName("content-box")

        box_two_layout = QGridLayout()
        box_two.setLayout(box_two_layout)

        box_two_layout.addWidget(QLabel("Decision Type:"), 0, 0)
        self.decision_type = QComboBox()
        self.decision_type.addItems(list(EDDC_DECISION_TYPE.keys()))
        box_two_layout.addWidget(self.decision_type, 0, 1, 1, 3)

        box_two_layout.addWidget(QLabel("Received Valid Between:"), 1, 0)
        self.received_valid_between_start = DateEdit()
        self.received_valid_between_start.setDisplayFormat("yyyy-MM-dd")
        self.received_valid_between_end = DateEdit()
        self.received_valid_between_end.setDisplayFormat("yyyy-MM-dd")
        box_two_layout.addWidget(self.received_valid_between_start, 1, 1)
        box_two_layout.addWidget(QLabel("and", maximumWidth=30), 1, 2)
        box_two_layout.addWidget(self.received_valid_between_end, 1, 3)

        box_two_layout.addWidget(QLabel("Issued Between:"), 2, 0)
        self.issued_between_start = DateEdit()
        self.issued_between_start.setDisplayFormat("yyyy-MM-dd")
        self.issued_between_end = DateEdit()
        self.issued_between_end.setDisplayFormat("yyyy-MM-dd")
        box_two_layout.addWidget(self.issued_between_start, 2, 1)
        box_two_layout.addWidget(QLabel("and", maximumWidth=30), 2, 2)
        box_two_layout.addWidget(self.issued_between_end, 2, 3)

        self.scroll_area_contents_layout.addWidget(box_two, 2, 0, 1, 2)

        # BOX 3
        box_three = QWidget()
        box_three.setObjectName("content-box")

        box_three_layout = QGridLayout()
        box_three.setLayout(box_three_layout)

        box_three_layout.addWidget(QLabel("Application Type:"), 0, 0)
        self.application_type = QComboBox()
        self.application_type.addItems(list(EDDC_APPLICATION_TYPE.keys()))
        box_three_layout.addWidget(self.application_type, 0, 1, 1, 3)

        box_three_layout.addWidget(QLabel("Appeal Method:"), 1, 0)
        self.appeal_method = QComboBox()
        self.appeal_method.addItems(list(EDDC_METHOD.keys()))
        box_three_layout.addWidget(self.appeal_method, 1, 1, 1, 3)

        box_three_layout.addWidget(QLabel("Appeal decision:"), 2, 0)
        self.appeal_decision = QComboBox()
        self.appeal_decision.addItems(list(EDDC_DECISION.keys()))
        box_three_layout.addWidget(self.appeal_decision, 2, 1, 1, 3)

        box_three_layout.addWidget(QLabel("Planning Inspectorate reference:"), 3, 0)
        self.inspectorate_reference = QLineEdit()
        box_three_layout.addWidget(self.inspectorate_reference, 3, 1, 1, 3)

        box_three_layout.addWidget(QLabel("Appeal decision between:"), 4, 0)
        self.appeal_decision_between_start = DateEdit()
        self.appeal_decision_between_start.setDisplayFormat("yyyy-MM-dd")

        self.appeal_decision_between_end = DateEdit()
        self.appeal_decision_between_end.setDisplayFormat("yyyy-MM-dd")

        box_three_layout.addWidget(self.appeal_decision_between_start, 4, 1)
        box_three_layout.addWidget(QLabel("and", maximumWidth=30), 4, 2)
        box_three_layout.addWidget(self.appeal_decision_between_end, 4, 3)

        self.scroll_area_contents_layout.addWidget(box_three, 3, 0, 1, 2)

        # BOTTOM BUTTONS
        bottom_buttons = QWidget()
        bottom_buttons_layout = QHBoxLayout()
        bottom_buttons.setLayout(bottom_buttons_layout)

        self.search = QPushButton("Search")
        self.search.clicked.connect(self.Search)
        bottom_buttons_layout.addWidget(self.search, alignment=QtCore.Qt.AlignTop)

        self.reset = QPushButton("Reset")
        self.reset.clicked.connect(self.Clear)
        bottom_buttons_layout.addWidget(self.reset, alignment=QtCore.Qt.AlignTop)

        self.scroll_area_contents_layout.addWidget(bottom_buttons, 6, 0, 1, 2)

        # ON SEARCH
        self.progress_bar_label = QLabel("Starting Session...")
        self.progress_bar_label.setObjectName("progress-label")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)

        # ------------------- END SCROLL -----------------------------

        scroll_area_contents.setLayout(self.scroll_area_contents_layout)
        scroll_area.setWidget(scroll_area_contents)
        layout.addWidget(scroll_area)

        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

        # CONTENTS
        self.line_edits = [
            self.application_number,
            self.address,
            self.proposal,
            self.agents_name,
            self.inspectorate_reference,

        ]
        self.combo_boxes = [
            self.parish,
            self.ward,
            self.decision_type,
            self.application_type,
            self.appeal_method

        ]
        self.date_edits = [
            self.appeal_decision_between_start,
            self.appeal_decision_between_end,
            self.issued_between_start,
            self.received_valid_between_start,
            self.issued_between_end,
            self.received_valid_between_end
        ]

    # Reset all values in input boxes
    def Clear(self):
        """
        Goes through each of of the input boxes and sets them to null values.
        :return: None
        """
        for line_edit in self.line_edits:
            line_edit.setText("")
        for combo_box in self.combo_boxes:
            combo_box.setCurrentIndex(0)
        for date_edit in self.date_edits:
            date_edit.active = False
            date_edit.reset = True
            date_edit.setSpecialValueText(" ")
            date_edit.setDate(QtCore.QDate.fromString("01/01/0001", "dd/MM/yyyy"))
            date_edit.reset = False

    def Search(self):
        self.scroll_area_contents_layout.addWidget(self.progress_bar_label, 4, 0, 1, 2)
        self.scroll_area_contents_layout.addWidget(self.progress_bar, 5, 0, 1, 2)

        # SELECT REFERENCE
        parish = EDDC_PARISH.get(self.parish.currentText())
        ward = EDDC_WARD.get(self.ward.currentText())
        decision_type = EDDC_DECISION_TYPE.get(self.decision_type.currentText())
        application_type = EDDC_APPLICATION_TYPE.get(self.application_type.currentText())
        appeal_method = EDDC_METHOD.get(self.appeal_method.currentText())
        appeal_decision = EDDC_DECISION.get(self.appeal_decision.currentText())

        build_request = {
            "ctl00_ContentPlaceHolder1_chkOutstanding": "on" if self.outstanding_only.checkState() else "",
            "ctl00$ContentPlaceHolder1$txtAppNumber": self.application_number.text(),
            "ctl00$ContentPlaceHolder1$txtAddress": self.address.text(),
            "ctl00$ContentPlaceHolder1$txtProposal": self.proposal.text(),
            "ctl00$ContentPlaceHolder1$txtAgentsName": self.agents_name.text(),
            "ctl00$ContentPlaceHolder1$ddlParish": parish,
            "ctl00$ContentPlaceHolder1$ddlWard": ward,
            "ctl00$ContentPlaceHolder1$ddlDecisionType": decision_type,
            "ctl00$ContentPlaceHolder1$txtDateReceivedFrom": self.received_valid_between_start.text(),
            "ctl00$ContentPlaceHolder1$txtDateReceivedTo": self.received_valid_between_end.text(),
            "ctl00$ContentPlaceHolder1$txtDateIssuedFrom": self.issued_between_start.text(),
            "ctl00$ContentPlaceHolder1$txtDateIssuedTo": self.issued_between_end.text(),
            "ctl00$ContentPlaceHolder1$ddlApplicationType": application_type,
            "ctl00$ContentPlaceHolder1$ddlAppealMethod": appeal_method,
            "ctl00$ContentPlaceHolder1$ddlAppealDecision": appeal_decision,
            "ctl00_ContentPlaceHolder1_txtPinsRef": self.inspectorate_reference.text(),
            "ctl00$ContentPlaceHolder1$txtDateAppealDecisionFrom": self.appeal_decision_between_start.text(),
            "ctl00$ContentPlaceHolder1$txtDateAppealDecisionTo": self.appeal_decision_between_end.text()
        }

        search_request = EDDC_search.EDDCSearch(request_data=build_request, settings=self.settings)

        # THREAD SIGNAL FUNCTIONS
        def update_progress(i):
            self.progress_bar.setValue(i)

        def update_progress_label(msg):
            self.progress_bar_label.setText(msg)
            self.progress_bar_label.updateGeometry()

        def update_progress_label_error():
            self.progress_bar_label.setStyleSheet("color: red;")

        def reset_signal():
            self.progress_bar_label.setStyleSheet("color: black;")
            self.progress_bar_label.setParent(None)
            self.progress_bar.setParent(None)
            self.scroll_area_contents_layout.removeWidget(self.progress_bar_label)
            self.scroll_area_contents_layout.removeWidget(self.progress_bar)
            self.progress_bar.setValue(0)
            self.progress_bar_label.setText("Starting Session...")

        def TooManyResults(number):
            too_many = TooManyResultsDialog(number)
            too_many.exec_()

        def saveFile(applications):
            path, extension = QFileDialog.getSaveFileName(filter="Excel Spreadsheet (*.xlsx)",
                                                          directory=f"{os.getcwd()}/Output CSV/Untitled")

            if extension == "Excel Spreadsheet (*.xlsx)":
                search_request.WriteXlSX(path, applications)
                dialog = FileSavedDialog()
                dialog.exec_()
            else:
                print("Unrecognised or no file extension")

            reset_signal()

        search_request.signals.too_many_results.connect(TooManyResults)
        search_request.signals.error.connect(update_progress_label_error)
        search_request.signals.progress.connect(update_progress)
        search_request.signals.message.connect(update_progress_label)
        search_request.signals.reset.connect(reset_signal)
        search_request.signals.finished.connect(saveFile)

        self.thread_pool.start(search_request)


app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec_()
