from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
from PyQt5 import QtCore
import sys
import os
import json
from datetime import date
import application_request
import threading
import time
import concurrent.futures
from select_reference import *

# DEVELOPMENT: Issues to test:
#   - No file name
#   - No internet connection


# Returns string formatted time
def clock():
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime())


# Writes invalid search to log.txt
def Log_Error(request):
    with open("log.txt", "a") as log_file:
        log_file.write(f"\n [INVALID REQUEST] {clock()} :: {json.dumps(request, indent=2)}")


# Signals for the search class
class SearchSignal(QtCore.QObject):
    progress = QtCore.pyqtSignal(int)
    message = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(bool)
    reset = QtCore.pyqtSignal()
    product = QtCore.pyqtSignal(object)


# Search as Qt Thread
class Search(QtCore.QRunnable):
    def __init__(self, request):
        super(Search, self).__init__()
        self.request = request
        self.signals = SearchSignal()

    @QtCore.pyqtSlot()
    def run(self):
        # Create search instance
        ap_request = application_request.ApplicationRequest(params=self.request)
        self.signals.message.emit(ap_request.createSession())
        response_valid, response_message = ap_request.searchRequest()

        if response_valid:
            self.signals.progress.emit(20)
            self.signals.message.emit(response_message)
        # If the http response is not valid: return
        else:
            self.signals.message.emit(response_message)
            self.signals.progress.emit(10)
            self.signals.error.emit(True)

            # WAIT then remove widget
            time.sleep(3)
            self.signals.reset.emit()
            return

        # DEVELOPMENT: Print the first page html
        # print(ap_request.HTTP_Responses["page=1"].decode("utf-8"))

        number_applications = ap_request.extractShowingInt()
        self.signals.message.emit(f"Search found {number_applications} applications...")
        self.signals.progress.emit(25)

        # STEP 3
        # Uses thread pool to open all pages and extract the html content
        # From original app request class def openPages(self):
        #
        # Uses thread pool to get all the pages of results at once. Takes progress from 25 to 90 (65)

        progress_per_page = int(65//ap_request.pages-1)
        progress = 25

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(ap_request.nextPage, i) for i in range(2, ap_request.pages + 1)]
            print("[LOG] Request threads started")
            for i, _ in enumerate(concurrent.futures.as_completed(futures)):
                progress += progress_per_page
                self.signals.message.emit(f"Searching page {i+2}")
                self.signals.progress.emit(progress)
            # concurrent.futures.wait(futures, return_when="ALL_COMPLETED")
            print("[LOG] Request threads finished")

        # By the end must always be 90% done
        self.signals.progress.emit(90)

        # EXTRACT DATA
        ap_request.ExtractData()
        self.signals.message.emit("Data extracted...")
        self.signals.progress.emit(100)

        self.signals.product.emit(ap_request.all_applications)


# Reimplemented date edit widget to allow for null values
class DateEdit(QDateEdit):
    popupSignal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(DateEdit, self).__init__(parent)
        self.setCalendarPopup(True)
        self.calendarWidget().installEventFilter(self)
        self.setMinimumDate(QtCore.QDate(2010, 1, 1))
        self.setSpecialValueText(" ")
        self.setDate(QtCore.QDate.fromString("01/01/0001", "dd/MM/yyyy"))
        self.active = False
        self.reset = False

    def resetIfNotActive(self):
        if not self.active and not self.reset:
            self.setDate(date.today())
            self.active = True

    def eventFilter(self, obj, event):
        if self.calendarWidget() is obj and event.type() == QtCore.QEvent.Show:
            self.popupSignal.emit()
            self.resetIfNotActive()

        return super(DateEdit, self).eventFilter(obj, event)


# noinspection PyArgumentList
class MainWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setWindowTitle("Planning - Applications Search")
        self.setMinimumSize(800, 800)
        self.setWindowIcon(QIcon(r"resources\icon.png"))

        # GUI THREAD POOL
        self.thread_pool = QtCore.QThreadPool()

        # Style
        style_sheet = open(r"resources\style.css").read()
        self.setStyleSheet(style_sheet)

        # Main Widget
        main_widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignHCenter)

        # Scroll Area
        scroll_area = QScrollArea()
        scroll_area.setMaximumWidth(780)
        scroll_area.setWidgetResizable(True)
        scroll_area_contents = QWidget()
        scroll_area_contents.setObjectName("scroll-area")
        self.scroll_area_contents_layout = QGridLayout()

        # ------------------- START SCROLL -----------------------------

        title = QLabel("Applications Search")
        title.setObjectName("title")
        self.scroll_area_contents_layout.addWidget(title, 0, 0, alignment=QtCore.Qt.AlignHCenter)

        # ------------ REFERENCE NUMBERS ---------------

        reference_label = QLabel("Reference Numbers")
        reference_label.setObjectName("section-header")
        self.scroll_area_contents_layout.addWidget(reference_label, 1, 0)

        reference = QWidget()
        reference.setObjectName("section")

        reference_layout = QGridLayout()
        reference_layout.setSpacing(10)
        reference_layout.setAlignment(QtCore.Qt.AlignLeft)

        # Reference layout contents
        reference_layout.addWidget(QLabel("Application Reference:"), 0, 0)
        self.application_reference = QLineEdit()
        reference_layout.addWidget(self.application_reference, 0, 1)
        reference_layout.addWidget(QLabel("Planning Portal Reference:"), 1, 0)
        self.planning_portal_reference = QLineEdit()
        reference_layout.addWidget(self.planning_portal_reference, 1, 1)
        reference_layout.addWidget(QLabel("Alternative Reference:"), 2, 0)
        self.alternative_reference = QLineEdit()
        reference_layout.addWidget(self.alternative_reference, 2, 1)

        reference.setLayout(reference_layout)
        self.scroll_area_contents_layout.addWidget(reference, 2, 0)

        # ------------ APPLICATION DETAILS --------------------

        application_label = QLabel("Application Details")
        application_label.setObjectName("section-header")
        self.scroll_area_contents_layout.addWidget(application_label, 3, 0)

        application = QWidget()
        application.setObjectName("section")

        application_layout = QGridLayout()
        application_layout.setSpacing(10)
        application_layout.setAlignment(QtCore.Qt.AlignLeft)

        # DESCRIPTION KEYWORD
        application_layout.addWidget(QLabel("Description Keyword:"), 0, 0)
        self.description_keyword = QLineEdit()
        application_layout.addWidget(self.description_keyword, 0, 1)
        application_layout.addWidget(QLabel("Applicant Name:"), 1, 0)
        self.applicant_name = QLineEdit()
        application_layout.addWidget(self.applicant_name, 1, 1)

        # APPLICATION TYPE
        application_layout.addWidget(QLabel("Application Type:"), 2, 0)
        self.application_type = QComboBox()
        self.application_type.addItems(list(CASE_TYPE.keys()))
        application_layout.addWidget(self.application_type)

        # WARD
        application_layout.addWidget(QLabel("Ward:"), 3, 0)
        self.ward = QComboBox()
        self.ward.addItems(list(WARD.keys()))
        application_layout.addWidget(self.ward)

        # CONSERVATION AREA
        application_layout.addWidget(QLabel("Conservation Area:"), 4, 0)
        self.conservation_area = QComboBox()
        self.conservation_area.addItems(list(CONSERVATION_AREA.keys()))
        application_layout.addWidget(self.conservation_area)

        # AGENT
        application_layout.addWidget(QLabel("Agent:"), 5, 0)
        self.agent = QLineEdit()
        application_layout.addWidget(self.agent)

        # STATUS
        application_layout.addWidget(QLabel("Status:"), 6, 0)
        self.status = QComboBox()
        self.status.addItems(list(STATUS.keys()))
        application_layout.addWidget(self.status)

        # DECISION
        application_layout.addWidget(QLabel("Decision:"), 7, 0)
        self.decision = QComboBox()
        self.decision.addItems(list(DECISION.keys()))
        application_layout.addWidget(self.decision)

        # APPEAL STATUS
        application_layout.addWidget(QLabel("Appeal Status:"), 8, 0)
        self.appeal_status = QComboBox()
        self.appeal_status.addItems(list(APPEAL_STATUS.keys()))
        application_layout.addWidget(self.appeal_status)

        # APPEAL DECISION
        application_layout.addWidget(QLabel("Appeal Decision:"), 9, 0)
        self.appeal_decision = QComboBox()
        self.appeal_decision.addItems(list(APPEAL_DECISION.keys()))
        application_layout.addWidget(self.appeal_decision)

        # _DEVELOPMENT TYPE
        application_layout.addWidget(QLabel("Development Type:"), 10, 0)
        self.development_type = QComboBox()
        self.development_type.addItems(list(DEVELOPMENT_TYPE.keys()))
        application_layout.addWidget(self.development_type)

        # ADDRESS
        application_layout.addWidget(QLabel("Address:"), 11, 0)
        self.address = QLineEdit()
        application_layout.addWidget(self.address)

        application.setLayout(application_layout)
        self.scroll_area_contents_layout.addWidget(application, 4, 0)

        # ----------- DATES ---------------

        dates_header = QLabel("Dates")
        dates_header.setObjectName("section-header")
        self.scroll_area_contents_layout.addWidget(dates_header, 5, 0)

        dates = QWidget()
        dates.setObjectName("section")

        dates_layout = QGridLayout()
        dates_layout.setSpacing(10)
        dates_layout.setAlignment(QtCore.Qt.AlignLeft)

        # DATE VALIDATED
        dates_layout.addWidget(QLabel("Date Validated:"), 0, 0)
        dates_layout.addWidget(QLabel("to:"), 0, 2)
        self.date_validated_start = DateEdit()
        self.date_validated_start.dateChanged.connect(self.date_validated_start.resetIfNotActive)
        self.date_validated_end = DateEdit()
        self.date_validated_end.dateChanged.connect(self.date_validated_end.resetIfNotActive)
        dates_layout.addWidget(self.date_validated_start, 0, 1)
        dates_layout.addWidget(self.date_validated_end, 0, 3)

        # DATE ACTUAL COMMITTEE
        dates_layout.addWidget(QLabel("Date Actual Committee:"), 1, 0)
        dates_layout.addWidget(QLabel("to:"), 1, 2)
        self.date_committee_start = DateEdit()
        self.date_committee_start.dateChanged.connect(self.date_committee_start.resetIfNotActive)
        self.date_committee_end = DateEdit()
        self.date_committee_end.dateChanged.connect(self.date_committee_end.resetIfNotActive)
        dates_layout.addWidget(self.date_committee_start, 1, 1)
        dates_layout.addWidget(self.date_committee_end, 1, 3)

        # DECISION DATE
        dates_layout.addWidget(QLabel("Decision Date:"), 2, 0)
        dates_layout.addWidget(QLabel("to:"), 2, 2)
        self.decision_date_start = DateEdit()
        self.decision_date_start.dateChanged.connect(self.decision_date_start.resetIfNotActive)
        self.decision_date_end = DateEdit()
        self.decision_date_end.dateChanged.connect(self.decision_date_end.resetIfNotActive)
        dates_layout.addWidget(self.decision_date_start, 2, 1)
        dates_layout.addWidget(self.decision_date_end, 2, 3)

        # APPEAL DECISION DATE
        dates_layout.addWidget(QLabel("Appeal Decision Date:"), 3, 0)
        dates_layout.addWidget(QLabel("to:"), 3, 2)
        self.appeal_decision_date_start = DateEdit()
        self.appeal_decision_date_start.dateChanged.connect(self.appeal_decision_date_start.resetIfNotActive)
        self.appeal_decision_date_end = DateEdit()
        self.appeal_decision_date_end.dateChanged.connect(self.appeal_decision_date_end.resetIfNotActive)
        dates_layout.addWidget(self.appeal_decision_date_start, 3, 1)
        dates_layout.addWidget(self.appeal_decision_date_end, 3, 3)

        dates.setLayout(dates_layout)
        self.scroll_area_contents_layout.addWidget(dates, 6, 0)

        # ------------ PAGE BOTTOM BUTTONS ----------------------

        page_bottom_buttons = QWidget()
        page_bottom_buttons.setObjectName("page-bottom-buttons")
        page_bottom_buttons_layout = QGridLayout()
        page_bottom_buttons_layout.setSpacing(10)
        page_bottom_buttons_layout.setAlignment(QtCore.Qt.AlignHCenter)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.Search)
        page_bottom_buttons_layout.addWidget(self.search_button, 0, 0)

        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.Clear)
        page_bottom_buttons_layout.addWidget(self.clear_button, 0, 1)

        page_bottom_buttons.setLayout(page_bottom_buttons_layout)
        self.scroll_area_contents_layout.addWidget(page_bottom_buttons, 9, 0)

        # ON SEARCH
        self.progress_bar_label = QLabel("Making Search Request...")
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
        self.combo_boxes = [
            self.application_type,
            self.ward,
            self.conservation_area,
            self.status,
            self.decision,
            self.appeal_status,
            self.appeal_decision,
            self.development_type

        ]
        self.line_edits = [
            self.application_reference,
            self.planning_portal_reference,
            self.alternative_reference,
            self.description_keyword,
            self.applicant_name,
            self.agent,
            self.address
        ]
        self.date_edits = [
            self.date_validated_start,
            self.date_validated_end,
            self.date_committee_start,
            self.date_committee_end,
            self.decision_date_start,
            self.decision_date_end,
            self.appeal_decision_date_start,
            self.appeal_decision_date_end
        ]
        self.all_input = self.combo_boxes + self.line_edits + self.date_edits

    # Reset all values in input boxes
    def Clear(self):
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

    # Carries out the search function
    def Search(self):
        # Fetch codes
        case_type = CASE_TYPE.get(self.application_type.currentText())
        ward = WARD.get(self.ward.currentText())
        conservation_area = CONSERVATION_AREA.get(self.conservation_area.currentText())
        status = STATUS.get(self.status.currentText())
        decision = DECISION.get(self.decision.currentText())
        appeal_decision = APPEAL_DECISION.get(self.appeal_decision.currentText())
        development_type = DEVELOPMENT_TYPE.get(self.development_type.currentText())

        # Create request
        raw_request = {
            "action": "firstPage",
            "org.apache.struts.taglib.html.TOKEN": "ff217d74428fe4d6687e6df9b66fa2eb",
            "searchCriteria.reference": self.application_reference.text(),
            "searchCriteria.planningPortalReference": self.planning_portal_reference.text(),
            "searchCriteria.alternativeReference": self.alternative_reference.text(),
            "searchCriteria.description": self.description_keyword.text(),
            "searchCriteria.applicantName": self.applicant_name.text(),
            "searchCriteria.caseType": case_type,
            "searchCriteria.ward": ward,
            "searchCriteria.conservationArea": conservation_area,
            "searchCriteria.agent": self.agent.text(),
            "searchCriteria.caseStatus": status,
            "searchCriteria.caseDecision": decision,
            "searchCriteria.appealStatus": self.appeal_status.currentText(),
            "searchCriteria.appealDecision": appeal_decision,
            "searchCriteria.developmentType": development_type,
            "caseAddressType": "Application",
            "searchCriteria.address": self.address.text(),
            "date(applicationValidatedStart)": self.date_validated_start.text(),
            "date(applicationValidatedEnd)": self.date_validated_end.text(),
            "date(applicationCommitteeStart)": self.date_committee_start.text(),
            "date(applicationCommitteeEnd)": self.date_committee_end.text(),
            "date(applicationDecisionStart)": self.decision_date_start.text(),
            "date(applicationDecisionEnd)": self.decision_date_end.text(),
            "date(appealDecisionStart)": self.appeal_decision_date_start.text(),
            "date(appealDecisionEnd)": self.appeal_decision_date_end.text(),
            "searchType": "Application"
        }

        # Filter request to only fields that have been input
        request = {}
        for key, value in raw_request.items():
            ignore = ["", " ", "All"]
            if value not in ignore:
                request[key] = value

        # TODO: Log searches to log file
        print(json.dumps(request, indent=2))

        # Add progress bar to layout
        self.scroll_area_contents_layout.addWidget(self.progress_bar_label, 7, 0)
        self.scroll_area_contents_layout.addWidget(self.progress_bar, 8, 0)
        self.progress_bar_label.setText("Searching...")
        self.progress_bar.setValue(10)

        # SEARCH THREAD
        search_thread = Search(request)

        # THREAD SIGNAL FUNCTIONS
        def update_progress(i):
            """
            Update the progress bar widget
            :return: None
            """
            self.progress_bar.setValue(i)

        def update_progress_label(msg):
            """
            Updates the message in the progress bar label
            :param msg:
            :return:
            """
            self.progress_bar_label.setText(msg)

        def update_progress_label_error(error):
            """
            Set the progress label to red if error signal is sent
            :param error:
            :return: None
            """
            if error:
                self.progress_bar_label.setStyleSheet("color: red;")

        def reset_signal():
            self.progress_bar_label.setStyleSheet("color: black;")
            self.progress_bar_label.setParent(None)
            self.progress_bar.setParent(None)
            self.scroll_area_contents_layout.removeWidget(self.progress_bar_label)
            self.scroll_area_contents_layout.removeWidget(self.progress_bar)

        def saveFile(all_applications):
            path = QFileDialog.getSaveFileName(filter="CSV (*.csv)", directory=f"{os.getcwd()}/Search_CSV")
            application_request.ApplicationRequest.WriteCSV(path, all_applications)

        # CONNECT SIGNAL FUNCTIONS
        search_thread.signals.progress.connect(update_progress)
        search_thread.signals.message.connect(update_progress_label)
        search_thread.signals.error.connect(update_progress_label_error)
        search_thread.signals.reset.connect(reset_signal)
        search_thread.signals.product.connect(saveFile)

        # START THREAD
        self.thread_pool.start(search_thread)


app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec_()
