from pprint import pprint
import concurrent.futures
import requests
from bs4 import BeautifulSoup
from PyQt5.QtCore import QRunnable
from signals import SearchSignals
from time import sleep
from datetime import date
import xlsxwriter
import re


class EDDCSearch(QRunnable):
    session = None
    pages = None
    view_state = {}
    HTTP_Responses = {}
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

        self.StartSession()
        self.signals.message.emit("Making search request...")
        self.signals.progress.emit(5)

        self.SearchRequest()
        self.signals.message.emit("Search results found...")
        self.signals.progress.emit(10)

        if self.NumberPages() > 30:
            self.signals.too_many_results.emit(self.pages)
            self.signals.error.emit()
            self.signals.message.emit("Too many pages of results!")
            self.signals.progress.emit(100)
            sleep(4)
            self.signals.reset.emit()
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

        TODO:
            - Check http status code
            - Check got all view state params
            - Check Response from post is valid

        """

        copyright_url = "https://eastplanning.dorsetcouncil.gov.uk/"
        self.session = requests.Session()

        copyright_response = self.session.get(copyright_url)
        print(f"[LOG] Got response {copyright_response}")

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
        output = {}
        if content:
            soup = BeautifulSoup(content, "html.parser")
        elif response:
            soup = BeautifulSoup(response.content, "html.parser")

        else:
            raise TypeError

        input_elements = soup.find_all("input")
        for element in input_elements:
            name = element.attrs.get("name")
            if name:
                if name.startswith("__"):
                    output[name] = element.attrs.get("value")

        return output

    # STEP 2
    # Make the search request
    def SearchRequest(self):

        # GO TO ADVANCED SEARCH
        search_url = "https://eastplanning.dorsetcouncil.gov.uk/advsearch.aspx"
        search_page = self.session.get(search_url)

        # with open("html_responses/AdvancedSearch.html", "w") as outfile:
        #     outfile.write(search_page.content.decode("utf-8"))

        # Starts with just the search button
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

            if "Date" in key:
                prepared_request.update(self._GenerateHiddenFields(key, value))
            else:
                prepared_request.update({key: value})

        pprint(prepared_request)
        # pprint(dict(self.session.cookies))

        search_response = self.session.post(url="https://eastplanning.dorsetcouncil.gov.uk/advsearch.aspx",
                                            data=prepared_request)

        self.HTTP_Responses["page=0"] = search_response.content

        print("Search Response: ", search_response)
        print("History: ", search_response.history)

    @staticmethod
    # PRIVATE - Generates hidden input fields
    def _GenerateHiddenFields(field, value):
        """
        :param field: The POST request field that will having the hidden fields generated for
        :param value: The input value entered into the input box
        :return: The dict containing the original field and values and also the new generated fields
        TODO Clean me up
        """
        # Keys
        dateInputKey = field + "$dateInput"
        dateInput_ClientKey = dateInputKey.replace("$", "_") + "_ClientState"
        calendar_SD_Key = field.replace("$", "_") + "_calendar_SD"
        calendar_AD_Key = field.replace("$", "_") + "_calendar_AD"
        Client_state_Key = field.replace("$", "_") + "_ClientState"

        # Values dependent on if there is a value input or not
        if value:
            split_date = value.split("-")
            dateInputValue = "/".join(reversed(split_date))
            extended_date = f"{value}-00-00-00"
            calendar_SD_Value = str([list(map(int, split_date))])
        else:
            dateInputValue = ""
            extended_date = ""
            calendar_SD_Value = "[]"

        dateInput_ClientValue = '{"enabled":true,"emptyMessage":"","validationText":"' + extended_date \
                                + '","valueAsString":"' + extended_date + \
                                '","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":"' + dateInputValue + '"}'

        calendar_AD_Value = f'[[1980,1,1],[2099,12,30],[{",".join(map(str, map(int, str(date.today()).split("-"))))}]]'

        # COMPILE INTO DICT
        output = {
            field: value,
            dateInputKey: dateInputValue,
            dateInput_ClientKey: dateInput_ClientValue,
            calendar_SD_Key: calendar_SD_Value,
            calendar_AD_Key: calendar_AD_Value,
            Client_state_Key: ""
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
            # TODO: Fix exception
            raise Exception

        # If there is pages
        header_parts = page_header.text.split()
        if len(header_parts) == 5:
            *_, number_pages = header_parts
            self.pages = int(number_pages)
        else:
            print("[ERROR] Unexpected page header")
            print(page_header)
            self.pages = 0

        print(f"[LOG] Found {self.pages} pages")
        return self.pages

    @staticmethod
    # PRIVATE - Creates the Target page index number
    def _GetPageTarget(index):
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
    def OpenPages(self):
        """
        TODO Check that pages all open with good http response
            perhaps some check if it is the expected page with a scrape

        :return:
        """
        event_target = "ctl00$ContentPlaceHolder1$lvResults$RadDataPager1$ctl01$ctl"

        progress = 10
        if self.pages > 1:
            progress_per_page = int(90 // (self.pages - 1))
        else:
            progress_per_page = 1

        for index in range(1, self.pages):
            derived_target = self._GetPageTarget(index)
            page_string = str(derived_target).rjust(2, "0")

            prepared_request = {"__EVENTTARGET": event_target + page_string}

            view_state = self._GetViewState(content=self.HTTP_Responses[f"page={index - 1}"])
            prepared_request.update(view_state)

            page_response = self.session.post(url="https://eastplanning.dorsetcouncil.gov.uk/searchresults.aspx",
                                              data=prepared_request)

            self.HTTP_Responses[f"page={index}"] = page_response.content
            progress += progress_per_page
            self.signals.progress.emit(progress)

            # with open(f"html_responses/page={index}.html", "w") as file:
            #     file.write(page_response.content.decode("utf-8"))

    # STEP 5
    def ExtractData(self):
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

        pprint(self.data_set)

    # STEP 6
    @staticmethod
    def WriteXlSX(path, applications):
        workbook = xlsxwriter.Workbook(path)
        bold = workbook.add_format({"bold": True})
        removed = workbook.add_format()
        removed.set_font_color('red')

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

            tree = re.search(r"/T|/REG", reference)

            if tree:
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

            if tree: continue

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

        try:
            workbook.close()
        except xlsxwriter.workbook.FileCreateError:
            print("File is open!")


if __name__ == '__main__':
    # Date format: yyyy-mm-dd
    test_request = {
        "ctl00$ContentPlaceHolder1$txtDateIssuedFrom": "2020-07-03",
        "ctl00$ContentPlaceHolder1$txtDateReceivedTo": "2020-07-15"
    }

    test = EDDCSearch(request_data=test_request)
    test.run()
