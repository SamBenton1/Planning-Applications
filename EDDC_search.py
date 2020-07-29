from pprint import pprint
import requests
from bs4 import BeautifulSoup
from PyQt5.QtCore import QRunnable
from signals import SearchSignals
from time import sleep
from datetime import date
import xlsxwriter
import re
from issues import Log
import json

with open("settings.json") as settings_file:
    settings = json.load(settings_file)


class EDDCSearch(QRunnable):
    session = None
    pages = None
    view_state = {}
    HTTP_Responses = {}
    prepared_request = {}
    data_set = []

    def __init__(self, request_data):
        super(EDDCSearch, self).__init__()
        self.signals = SearchSignals()
        self.request = request_data

    def run(self):
        """
        Executed thread by QThreadPool, Manages signals and requests
        :return:
        """

        def ErrorSignal(msg):
            self.signals.error.emit()
            self.signals.message.emit(msg)
            self.signals.progress.emit(100)
            sleep(4)
            self.signals.reset.emit()

        if not self.StartSession():
            ErrorSignal("No Internet Connection")
            return

        self.signals.message.emit("Making search request...")
        self.signals.progress.emit(5)

        self.SearchRequest()

        self.signals.message.emit("Search results found...")
        self.signals.progress.emit(10)

        if not self.NumberPages():
            ErrorSignal("An error occurred when collecting results. Check the log for more info.")
            return

        if self.pages > settings["page_limit"]:
            self.signals.too_many_results.emit(self.pages)
            ErrorSignal("Too many pages of results!")
            return

        self.signals.message.emit(f"Opening {self.pages} pages...")
        self.OpenPages()
        self.ExtractData()
        self.signals.message.emit(f"Search returned {len(self.data_set)} results")
        self.signals.progress.emit(100)

        self.signals.finished.emit(self.data_set)

    # STEP 1
    # Start the session with the server
    def StartSession(self):
        """
        Starts the session by accessing the index page for the planning board.
        :return: Boolean value for session stated status
        """

        copyright_url = "https://eastplanning.dorsetcouncil.gov.uk/"
        self.session = requests.Session()

        # Check internet connection & start session
        try:
            copyright_response = self.session.get(copyright_url)
        except requests.exceptions.ConnectionError:
            return False

        # Check status code
        if copyright_response.status_code != 200:
            Log(f"Unexpected http response status code <{copyright_response.status_code}>")
            return False

        print(f"[LOG] Website responded with {copyright_response}")

        # Make request dict
        copyright_accept_request = self._GetViewState(copyright_response)
        copyright_accept_request.update({"ctl00$ContentPlaceHolder1$btnAccept": "Accept"})

        # ACCEPT TERMS
        disclaimer_url = "https://eastplanning.dorsetcouncil.gov.uk/disclaimer.aspx?returnURL=%2f%3fAspxAutoDetectCookieSupport%3d1"
        terms_response = self.session.post(url=disclaimer_url,
                                           data=copyright_accept_request)

        print(f"[LOG] Accepted terms {terms_response}")
        return True

    # PRIVATE - Extracts view state from response
    @staticmethod
    def _GetViewState(response=None, content=None):
        """
        Given only a response object or response content, this method extracts the view state parameters needed
        for session persistence whilst interacting with the ASP.NET server.
        :param response: Response object
        :param content: Response content
        :return: Dictionary with view state parameters
        """
        output = {}
        if content:
            soup = BeautifulSoup(content, "html.parser")
        elif response:
            soup = BeautifulSoup(response.content, "html.parser")
        else:
            Log("Protected class _GetViewState got unexpected arguments")
            return output

        input_elements = soup.find_all("input")
        for element in input_elements:
            name = element.attrs.get("name")
            if name:
                if name.startswith("__"):
                    output[name] = element.attrs.get("value")

        # Output is view state params dict
        return output

    # STEP 2
    # Make the search request
    def SearchRequest(self):
        """
        Compiles a dict which is then posted to the server in order to later get back search results.

        :return: Boolean value of if the response from the post request was valid
        """

        # GO TO ADVANCED SEARCH
        search_url = "https://eastplanning.dorsetcouncil.gov.uk/advsearch.aspx"
        search_page = self.session.get(search_url)

        # Initialise the request params with an empty dict
        prepared_request = {}

        # Get the view states
        view_states = self._GetViewState(search_page)
        prepared_request.update(view_states)

        # Add search button
        search_btn = {'ctl00$ContentPlaceHolder1$btnSearch3': 'Search'}
        prepared_request.update(search_btn)

        # Check for dates and if fields are empty
        for key, value in self.request.items():
            if not value:
                continue
            if value == " ":
                continue

            # Generate ASP.NET hidden input fields according to the dates
            if "Date" in key:
                prepared_request.update(self._GenerateHiddenFields(key, value))
            else:
                prepared_request.update({key: value})

        # pprint(prepared_request)
        self.prepared_request = prepared_request

        # POST request parameters to the server
        search_response = self.session.post(url="https://eastplanning.dorsetcouncil.gov.uk/advsearch.aspx",
                                            data=prepared_request)

        print(f"[LOG] Search POST request {search_response}")

        if not search_response.ok:
            Log(f"Bad http response from POST request {search_response}", request=prepared_request)

        self.HTTP_Responses["page=0"] = search_response.content
        print(f"[LOG] First search page retrieved with {search_response}")

    @staticmethod
    # PRIVATE - Generates hidden input fields
    def _GenerateHiddenFields(field, value):
        """
        :param field: The POST request field that will having the hidden fields generated for
        :param value: The input value entered into the input box
        :return: The dict containing the original field and values and also the new generated fields
        """
        # Keys
        date_input_key = field + "$dateInput"
        date_input_client_key = date_input_key.replace("$", "_") + "_ClientState"
        calendar_sd_key = field.replace("$", "_") + "_calendar_SD"
        calendar_ad_key = field.replace("$", "_") + "_calendar_AD"
        client_state_key = field.replace("$", "_") + "_ClientState"

        # Values dependent on if there is a value input or not
        if value:
            split_date = value.split("-")
            date_input_value = "/".join(reversed(split_date))
            extended_date = f"{value}-00-00-00"
            calendar_sd_value = str([list(map(int, split_date))])
        else:
            date_input_value = ""
            extended_date = ""
            calendar_sd_value = "[]"

        date_input_client_value = '{"enabled":true,"emptyMessage":"","validationText":"' + extended_date \
                                  + '","valueAsString":"' + extended_date + \
                                  '","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00",' \
                                  '"lastSetTextBoxValue":"' + date_input_value + '"} '

        calendar_ad_value = f'[[1980,1,1],[2099,12,30],[{",".join(map(str, map(int, str(date.today()).split("-"))))}]]'

        # COMPILE INTO DICT
        output = {
            field: value,
            date_input_key: date_input_value,
            date_input_client_key: date_input_client_value,
            calendar_sd_key: calendar_sd_value,
            calendar_ad_key: calendar_ad_value,
            client_state_key: ""
        }

        return output

    # STEP 3
    # Determine the number of pages to extract
    def NumberPages(self):
        """
        Soup the first page and get the header from which extract the number of pages.

        :return: Int number of pages
        """
        soup = BeautifulSoup(self.HTTP_Responses["page=0"], "html.parser")
        page_header = soup.find("div", id="ctl00_ContentPlaceHolder1_lvResults_RadDataPager1")

        if not page_header:
            Log("Unexpected page header, likely due to one page of results.", request=self.prepared_request)
            return False

        # If there is pages
        header_parts = page_header.text.split()
        if len(header_parts) == 5:
            *_, number_pages = header_parts
            self.pages = int(number_pages)
        else:
            Log("[ERROR] Unexpected page header")
            print(page_header)
            self.pages = 0

        print(f"[LOG] Found {self.pages} pages")
        return self.pages

    @staticmethod
    # PRIVATE - Creates the Target page index number
    def _GetPageTarget(index):
        """
        Works out what the target index will be for the request
        :param index: The actual page number that is being requested
        :return: The index that will be in the event target parameter
        """
        if index < 11:
            return index
        tens, units = str(index)
        if index == 11:
            return 2

        if units == "0":
            return 11
        else:
            return int(units) + 1

    # STEP 4
    # Request each page of results.
    def OpenPages(self):
        """
        Unlike the Poole search this one does not use threading and the ASP.NET event validator from the
        previous page is needed. Requests each page in series
        :return: None
        """
        event_target = "ctl00$ContentPlaceHolder1$lvResults$RadDataPager1$ctl01$ctl"

        # Work out how much progress each page is
        progress = 10
        if self.pages > 1:
            progress_per_page = int(90 // (self.pages - 1))
        else:
            progress_per_page = 1

        # Open each page
        for index in range(1, self.pages):
            derived_target = self._GetPageTarget(index)
            page_string = str(derived_target).rjust(2, "0")

            prepared_request = {"__EVENTTARGET": event_target + page_string}

            view_state = self._GetViewState(content=self.HTTP_Responses[f"page={index - 1}"])
            prepared_request.update(view_state)

            page_response = self.session.post(url="https://eastplanning.dorsetcouncil.gov.uk/searchresults.aspx",
                                              data=prepared_request)

            if page_response.status_code != 200:
                Log(f"Tried to open page {index - 1} of results but got bad status code {page_response.status_code}")

            # Save the response content in dict
            self.HTTP_Responses[f"page={index}"] = page_response.content
            progress += progress_per_page
            self.signals.progress.emit(progress)

    # STEP 5
    # Use scraping to extract the data from the results page
    def ExtractData(self):
        """
        Extract the data from each response page and store it in a dict which is then appended to the master
        data set which is returned from the Run method in the form of a pyqtSignal.

        NOTE: This method should only be called if it has been determined that each of the response.contents
        have a results list present on them as no check is done in this method and an exception will be raised.

        :return: the list dataset
        """
        for page, content in self.HTTP_Responses.items():
            soup = BeautifulSoup(content, "html.parser")
            results_area = soup.find("div", id="news_results_list")
            results = results_area.find_all("div", attrs={"class": "emphasise-area"})
            for result in results:
                reference = result.find("h2")
                url = reference.a.attrs["href"]
                reference = reference.text

                fields = result.find_all("p")
                fields = [para.text for para in fields]
                location, proposal, *Decision = fields
                if Decision:
                    decision, decision_date = Decision
                    is_app = False
                else:
                    is_app = True
                    decision = decision_date = ""

                application_data = {
                    "Reference": reference,
                    "Location": location,
                    "Proposal": proposal,
                    "Decision": decision,
                    "Decision Date": decision_date,
                    "_url": url,
                    "_Application": is_app
                }
                # pprint(application_data)
                self.data_set.append(application_data)

        # pprint(self.data_set)
        print(f"[LOG] Data set created")
        return self.data_set

    # STEP 6
    @staticmethod
    def WriteXlSX(path, applications):
        workbook = xlsxwriter.Workbook(path)
        bold = workbook.add_format({"bold": True})
        removed = workbook.add_format()
        removed.set_font_color('red')

        def advanced_output():
            all_worksheet = workbook.add_worksheet(name="All")

            apps_worksheet = workbook.add_worksheet(name="Applications")
            apps_index = 1

            dec_worksheet = workbook.add_worksheet(name="Decisions")
            decs_index = 1

            HEADERS = ["Reference", "Location", "Proposal", "Decision", "Date"]

            all_worksheet.write_row(0, 0, data=HEADERS, cell_format=bold)
            apps_worksheet.write_row(0, 0, HEADERS[:3], cell_format=bold)
            dec_worksheet.write_row(0, 0, HEADERS, cell_format=bold)

            for i, app in enumerate(applications):
                values = [value for value in app.values()]
                print(values)
                reference, location, proposal, decision, decision_date, url, app = values

                excluded = True
                if not re.search(r"/T|/REG", reference) and re.search(r"BH21", location) and not re.search(r"BH21 6",
                                                                                                           location):
                    excluded = False

                if excluded:
                    is_removed = removed
                else:
                    is_removed = None

                all_worksheet.write_url(i + 1, 0, f"https://eastplanning.dorsetcouncil.gov.uk/{url}",
                                        is_removed,
                                        reference)
                all_worksheet.write(i + 1, 1, location, is_removed)
                all_worksheet.write(i + 1, 2, proposal, is_removed)
                all_worksheet.write(i + 1, 3, decision, is_removed)
                all_worksheet.write(i + 1, 4, decision_date, is_removed)

                if excluded: continue

                if app:
                    apps_worksheet.write_url(apps_index, 0, url=f"https://eastplanning.dorsetcouncil.gov.uk/{url}",
                                             string=reference)
                    apps_worksheet.write(apps_index, 1, location)
                    apps_worksheet.write(apps_index, 2, proposal)
                    apps_index += 1
                else:
                    dec_worksheet.write_url(decs_index, 0, url=f"https://eastplanning.dorsetcouncil.gov.uk/{url}",
                                            string=reference)
                    dec_worksheet.write(decs_index, 1, location)
                    dec_worksheet.write(decs_index, 2, proposal)
                    dec_worksheet.write(decs_index, 3, decision)
                    dec_worksheet.write(decs_index, 4, decision_date)
                    decs_index += 1

        def simple_output():
            all_worksheet = workbook.add_worksheet(name="All")

            index = 0

            for data in applications:
                values = [value for value in data.values()]
                print(values)
                reference, location, proposal, decision, decision_date, url, app = values

                all_worksheet.write_url(index, 0, f"https://eastplanning.dorsetcouncil.gov.uk/{url}", string=reference)
                index += 1
                all_worksheet.write(index, 0, location)
                index += 1
                all_worksheet.write(index, 0, proposal)
                index += 1

                if decision:
                    all_worksheet.write(index, 0, decision)
                    index += 1
                    all_worksheet.write(index, 0, decision_date)
                    index += 1

        if settings["simple_output"]:
            simple_output()
        else:
            advanced_output()

        try:
            workbook.close()
        except xlsxwriter.workbook.FileCreateError:
            Log("Unable to write xlsx file as permission was denied by the OS")
