import json
import requests
from bs4 import BeautifulSoup
from PyQt5.QtCore import *
import time
import concurrent.futures
import xlsxwriter
from issues import Log
from signals import SearchSignals


# Returns string formatted time
def clock():
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime())


class PooleSearch(QRunnable):
    URL = "https://boppa.poole.gov.uk/online-applications/advancedSearchResults.do"

    # DECLARE ATTRIBUTES
    session = all_applications = None
    HTTP_Responses = {}
    total_search_results = pages = 0
    data_set = None

    def __init__(self, params):
        super(PooleSearch, self).__init__()

        # SEARCH PARAMETERS
        self.request_params = params
        self.signals = SearchSignals()

    # CLASS THREAD
    def run(self):
        wait = time.sleep

        # BASIC ERROR
        def Error(msg):
            self.signals.progress.emit(100)
            self.signals.error.emit()
            self.signals.message.emit(msg)

            wait(3)
            self.signals.reset.emit()

        # START SESSION
        if self.StartSession():
            self.signals.progress.emit(5)
            self.signals.message.emit("Session started...")
        else:
            "Failed to start session... [SEE LOG]"
            return

        # START SEARCH
        response_ok, response_message = self.SearchRequest()
        if response_ok:
            self.signals.progress.emit(10)
            self.signals.message.emit("Search found results...")

            # If there is only one result then read that page.
            if response_message == "single":
                self.signals.message.emit("Search Completed")
                self.signals.progress.emit(100)
                self.signals.finished.emit(self.data_set)
                return
        else:
            # Response message got from page
            Error(response_message)
            return

        # GET THE NUMBER OF RESULTS ON THE PAGE
        number_results = self.NumberResults()
        self.signals.progress.emit(15)
        self.signals.message.emit(f"Found {number_results} results over {self.pages} pages...")

        if self.pages > 30:
            Error("Too many pages will open")
            self.signals.too_many_results.emit(self.pages)

        # OPEN ALL SUBSEQUENT PAGES
        self.OpenPages()

        # EXTRACT DATA FROM HTTP RESPONSES
        self.ExtractData()

        # SAVE DATA
        self.signals.message.emit("Search Completed")
        self.signals.progress.emit(100)
        self.signals.finished.emit(self.data_set)

    # STEP 1
    def StartSession(self):
        """
        Starts session with poole.gov.uk website to obtain cookie for the search.
        :return: Boolean value of if session starting was successful
        """
        self.session = requests.Session()
        main_url = r"https://boppa.poole.gov.uk/online-applications/search.do?action=advanced&searchType=Application"

        try:
            response = self.session.get(main_url)
        except requests.exceptions.ConnectionError:
            Log("No Internet Connection")
            return False

        if not response.ok:
            Log(f"Bad Http response when starting session, status code <{response.status_code}>")
            return False

        print("[LOG] Started Session")
        return True

    # STEP 2
    # Initial Search request
    def SearchRequest(self):
        """
        Makes the initial search request with all search criteria
        :return: HTTP response content
        """

        # Create the url to which the get request will be made
        request = requests.Request("GET", self.URL, params=self.request_params)
        prepared = request.prepare()
        print(f"[LOG] GET request to {prepared.url}")

        # Make the get request
        response = self.session.get(self.URL, params=self.request_params)

        # SEND TO RESPONSE CHECK METHOD
        response_valid, response_message = self._CheckRequest(response=response)

        if response_valid:
            self.HTTP_Responses["page=1"] = response.content

        return response_valid, response_message

    # PRIVATE - Checks the first page to make sure that it is showing search results
    def _CheckRequest(self, response):
        """
        Check the response and all the possibilities to determine if the search was a success or not

        STEP I: Check status code
        STEP II: Check page title
        STEP III: If back on search page, check for message box
        STEP IV: Check if the page is a response page

        :param response: http response from GET request
        :return: Boolean and message as to whether the page is valid results or not.
        """

        # STEP I:
        if not response.ok:
            print(f"[LOG] Bad http response. Status Code <{response.status_code}>")
            return False, "Server Error"

        # STEP II:
        soup = BeautifulSoup(response.content, "html.parser")
        raw_page_title = soup.find("title")

        if not raw_page_title:
            Log(f"Web page title not found.", request=self.request_params)
            return False, "Page title not found"
        else:
            page_title = raw_page_title.text.strip()

        if page_title == "Search Results":
            return True, "page"
        elif page_title == "Applications Search":

            # STEP III
            message = soup.find("div", attrs={"class": "messagebox"})
            error_message = soup.find("div", attrs={"class": "messagebox errors"})

            if message:
                return False, " ".join(message.text.split("\n"))
            elif error_message:
                return False, " ".join(error_message.text.split("\n"))
            else:
                return False, "No Error Message found"
        else:
            if self._SinglePageDataExtraction(soup=soup, response=response):
                return True, "single"
            else:
                Log("Unexpected page title", request=self.request_params)
                return False, "Unexpected page title"

    # STEP 3
    # Gets the number of results and pages from the first page
    def NumberResults(self):
        """
        Uses html parser to pick out number of items showing and calculate the number of pages for viewing.
        :return: Int Number of results
        """

        # Check the Http response is present
        page_one_html = self.HTTP_Responses.get("page=1")
        if page_one_html is None:
            raise ValueError

        # Showing element at the bottom of the page
        soup = BeautifulSoup(page_one_html, "html.parser")
        showing_element = soup.find("span", attrs={"class": "showing"})

        # Less than a full page of results
        if not showing_element:
            # Locate search results
            search_results = soup.find("ul", id="searchresults")
            self.pages = 1
            self.total_search_results = len(search_results.find_all("li"))
            print(f"[LOG] {self.total_search_results} applications found over {self.pages} pages")
            return self.total_search_results

        # If there is more than one page of results look at the showing div
        raw_total_applications = showing_element.text
        raw_showing, total_applications = raw_total_applications.split(" of ")
        showing = int(raw_showing[-2:])
        self.total_search_results = int(total_applications)
        self.pages = (self.total_search_results // showing) + 1
        print(f"[LOG] {self.total_search_results} applications found over {self.pages} pages")

        return self.total_search_results

    # STEP 3 (ALTERNATIVE)
    def _SinglePageDataExtraction(self, soup, response):
        """
        Uses data scraping to get data from the single page
        :param soup: BeautifulSoup object
        :param response: the Requests response object
        :return: Boolean of whether the data has been extracted from a single page
        """

        heading = soup.find("div", id="pageheading")
        if heading:
            if heading.h1.text == "Planning – Application Summary":
                table = soup.find("table", id="simpleDetailsTable")

                rows = table.find_all("tr")
                table_values = {}
                for row in [row.findChild() for row in rows]:
                    key = row.text.strip()
                    value = row.find_next_sibling().text.strip()
                    table_values[key] = value

                self.data_set = [
                    {
                        "Address": table_values.get("Address"),
                        "Title": table_values.get("Proposal"),
                        "Received": table_values.get("Application Received"),
                        "Validated": table_values.get("Application Validated"),
                        "Status": table_values.get("Status"),
                        "Ref. No:": table_values.get("Reference"),
                        "Url": response.url
                    }
                ]
                if any(self.data_set) is None:
                    Log("Single page, didn't find table row", request=self.data_set)

                return True

        return False

    # STEP 4
    # Opens all the rest of the pages.
    def OpenPages(self):
        """
        Uses concurrent.futures ThreadPoolExecutor to open all the pages quickly and extract the html from them.
        :return: None
        """
        progress_per_page = int(75 // self.pages - 1)
        progress = 15

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self._NextPage, i) for i in range(2, self.pages + 1)]

            for i, _ in enumerate(concurrent.futures.as_completed(futures)):
                progress += progress_per_page
                self.signals.message.emit(f"Searching page {i + 2}...")
                self.signals.progress.emit(progress)

        # By the end must always be 90% done
        self.signals.progress.emit(90)
        print("[LOG] Opened all pages")

    # PRIVATE - Opens an page of index x and reads the content
    def _NextPage(self, page_index):
        """
        Gets the HTTPs response for all the following pages of results using the cookie send form the original request

        :param page_index: the index of the page being requested
        :return: None
        """

        # Raise value error if the entered page index is out of range
        if page_index > self.pages or page_index < 1:
            print("[ERROR] Invalid page index")
            raise ValueError

        params = {
            "action": "page",
            "searchCriteria.page": str(page_index)
        }

        response = self.session.get(self.URL, params=params)

        # LOG for each page that a good http response is received
        if response.ok:
            print(f"[LOG] Good http response {response.status_code}")
        else:
            Log(f"Bad http response {response.status_code}")

        self.HTTP_Responses[f"page={page_index}"] = response.content
        print(f"[LOG] HTTP response for page {page_index} collected")

    # STEP 5
    # Extracts the data by scraping the request data content
    def ExtractData(self):
        """
        Extracts the data using scraping from each of the http responses.

        :return: Json data set for all pages
        """
        self.data_set = []

        for response in self.HTTP_Responses:
            soup = BeautifulSoup(self.HTTP_Responses[response], "html.parser")
            search_results = soup.find("ul", id="searchresults")

            # Where all applications from this page are added to
            page_applications = []

            for li in search_results.find_all("li"):
                # Extract url and title
                application_link = li.a.attrs["href"]
                application_title = li.a.text.strip().strip("\r\n").strip()
                # application_title = f'"{application_title}"'

                # Get the meta data
                address_element, meta_element = li.find_all("p")
                address = address_element.text.strip()
                # address = f'"{address}"'
                meta = meta_element.text.strip()
                data = " ".join(meta.split())
                values = [value for value in data.split(" | ")]
                ref_no, received, validated, status = values

                # CONSTRUCT dict for application data
                application_data = {
                    "Address": address,
                    "Title": application_title,
                    "Received": received.lstrip("Received: "),
                    "Validated": validated.lstrip("Validated: "),
                    "Status": status.lstrip("Status: "),
                    "Ref. No:": ref_no.lstrip("Ref. No: "),
                    "Url": "https://boppa.poole.gov.uk" + application_link,
                }

                page_applications.append(application_data)

            print(f"[LOG] Got data from {response}")
            self.data_set.extend(page_applications)

        return self.data_set

    # STEP 6
    # Writes data to a csv file
    @staticmethod
    def WriteCSV(path, applications):
        """
        Edit the data and write to CSV file.
        :param applications:
        :param path: Got from QFileDialog
        :return: None
        """
        out_put_string = "Address, Title, Received, Validated, Status, Ref. No, Url,\n"

        # Clean data and join onto string
        for application_dict in applications:
            csv_config_data = [f'"{value}"' if "," in value else value for value in list(application_dict.values())]
            csv_line = ",".join(csv_config_data) + "\n"
            out_put_string += csv_line

        # Write multiline string to csv file
        with open(path[0], "w") as outfile:
            outfile.write(out_put_string)

    # STEP 6
    # Writes data to xlsx file
    @staticmethod
    def WriteXLSX(path, applications):
        print("Writing XLSX")
        workbook = xlsxwriter.Workbook(path)

        # Add a new worksheet
        worksheet = workbook.add_worksheet()
        bold = workbook.add_format({"bold": True})

        # Write headers
        headers = ["Address", "Title", "Received", "Validated", "Status", "Ref. No", "Url"]
        worksheet.write_row(0, 0, headers, bold)

        for index, app in enumerate(applications):
            values = list(app.values())
            worksheet.write_row(index + 1, 0, values)

        workbook.close()
