import requests
from bs4 import BeautifulSoup
import itertools


# FIXME: This Search
#     {
#       "action": "firstPage",
#       "searchCriteria.conservationArea": "CA14",
#       "caseAddressType": "Application",
#       "date(applicationValidatedStart)": "15/05/2020",
#       "date(applicationValidatedEnd)": "16/07/2020",
#       "searchType": "Application"
#     }

class ApplicationRequest(object):
    simple_search = r"https://boppa.poole.gov.uk/online-applications/simpleSearchResults.do"
    advance_search = r"https://boppa.poole.gov.uk/online-applications/advancedSearchResults.do"

    # DEVELOPMENT: send request to http bin:
    #   advance_search = r"http://httpbin.org/get"

    def __init__(self, params, search_type="advanced"):

        # TYPE OF SEARCH
        if search_type == "advanced":
            self.URL = self.advance_search
        else:
            self.URL = self.simple_search

        # SEARCH PARAMETERS
        self.request_params = params

        # DECLARE ATTRIBUTES
        self.session = self.all_applications = None
        self.HTTP_Responses = {}
        self.total_search_results = self.pages = 0

    def createSession(self):
        self.session = requests.Session()
        search_url = r"https://boppa.poole.gov.uk/online-applications/search.do?action=advanced&searchType=Application"
        try:
            response = self.session.get(search_url)
        except requests.exceptions.ConnectionError:
            print("No Internet Connection")
            return None

        return "Started Session..."

    # STEP 1
    # Initial Search request
    def searchRequest(self):
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
        response_valid, response_message = self._checkRequest(response=response)

        if response_valid:
            self.HTTP_Responses["page=1"] = response.content

        print(response_message)
        return response_valid, response_message

    @staticmethod
    # Private - Checks the first page to make sure that it is showing search results
    def _checkRequest(response):
        """
        Check the response and all the possibilities to determine if the search was a success or not

        STEP 1: Check status code
        STEP 2: Check page title
        STEP 3: If back on search page, check for message box

        :param response: http response from GET request
        :return: Boolean and message as to whether the page is valid results or not.
        """

        if not response.ok:
            print(f"[LOG] Bad http response. Status Code <{response.status_code}>")
            return False, "Server Error"

        soup = BeautifulSoup(response.content, "html.parser")
        raw_page_title = soup.find("title")

        if not raw_page_title:
            # TODO: Fix exceptions
            raise Exception
        else:
            page_title = raw_page_title.text.strip()

        # print("Page Title: ", page_title)

        if page_title == "Search Results":
            return True, "Results Found..."
        elif page_title == "Applications Search":
            message = soup.find("div", attrs={"class": "messagebox"})
            error_message = soup.find("div", attrs={"class": "messagebox errors"})

            if message:
                return False, " ".join(message.text.split("\n"))
            elif error_message:
                return False, " ".join(error_message.text.split("\n"))
            else:
                # DEVELOPMENT: Save error html to failed.html
                with open("failed.html", "w") as error_file:
                    print("writing error html")
                    error_file.write(response.content.decode("utf-8"))

                return False, "No Error Message found"
        else:
            print("Unexpected page title")
            # TODO: Fix Exception
            raise Exception

    # STEP 2
    # Gets the number of results and pages from the first page
    def extractShowingInt(self):
        """
        Uses html parser to pick out number of items showing and calculate the number of pages for viewing.
        :return: Number of pages
        """

        # Check the Http response is present
        page_one_html = self.HTTP_Responses.get("page=1")
        if page_one_html is None:
            raise ValueError

        # Showing element at the bottom of the page
        soup = BeautifulSoup(page_one_html, "html.parser")
        showing_element = soup.find("span", attrs={"class": "showing"})

        if not showing_element:
            # FIXME: If less that 10 results cannot gather the number of results
            return 0

        raw_total_applications = showing_element.text
        raw_showing, total_applications = raw_total_applications.split(" of ")
        showing = int(raw_showing[-2:])
        self.total_search_results = int(total_applications)
        self.pages = (self.total_search_results // showing) + 1
        print(f"[LOG] {self.total_search_results} applications found over {self.pages} pages")

        return self.total_search_results

    # Opens an page of index x and reads the content
    def nextPage(self, page_index):
        """
        Gets the HTTPs response for all the following pages of results using the cookie send form the original request

        :param page_index: the index of the page being requested
        :return: the HTTP response content for that page index
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
            print(f"[LOG] Bad http response {response.status_code}")

        self.HTTP_Responses[f"page={page_index}"] = response.content
        print(f"[LOG] HTTP response for page {page_index} collected")

        return

    # STEP 4
    # Extracts the data by scraping the request data content
    def ExtractData(self):
        """
        Extracts the data using scraping from each of the http responses.

        :return: Json data set for all pages
        """
        data_set = {}

        for response in self.HTTP_Responses:
            soup = BeautifulSoup(self.HTTP_Responses[response], "html.parser")
            search_results = soup.find("ul", id="searchresults")

            # Where all applications from this page are added to
            page_applications = []

            for li in search_results.find_all("li"):
                # Extract url and title
                application_link = li.a.attrs["href"]
                application_title = li.a.text.strip().strip("\r\n").strip()
                application_title = f'"{application_title}"'

                # Get the meta data
                address_element, meta_element = li.find_all("p")
                address = address_element.text.strip()
                address = f'"{address}"'
                meta = meta_element.text.strip()
                data = " ".join(meta.split())
                values = [value for value in data.split(" | ")]
                ref_no, received, validated, status = values

                # construct data dict
                application_data = {
                    "Address": address,
                    "Title": application_title,
                    "Received": received.lstrip("Received: "),
                    "Validated": validated.lstrip("Validated: "),
                    "Status": status.lstrip("Status: "),
                    "Ref. No:": ref_no.lstrip("Ref. No: "),
                    "Url": application_link,
                }

                page_applications.append(application_data)

            print(f"[LOG] Got data from {response}")
            data_set[response] = page_applications

            # Join applications from all pages to one list
            self.all_applications = list(itertools.chain.from_iterable(list(data_set.values())))

        # DEVELOPMENT: Printing of all search results
        # print(json.dumps(data_set, indent=2))

        return data_set

    # STEP 5
    # Writes data to a csv file
    @staticmethod
    def WriteCSV(path, applications):
        """

        :param applications:
        :param path:
        :return:
        """
        out_put_string = "Address, Title, Received, Validated, Status, Ref. No, Url,\n"
        for application_dict in applications:
            csv_line = ",".join(list(application_dict.values())) + "\n"
            out_put_string += csv_line
        with open(path[0], "w") as outfile:
            outfile.write(out_put_string)


def Test():
    request = {
        "action": "firstPage",
        # "org.apache.struts.taglib.html.TOKEN": "ff217d74428fe4d6687e6df9b66fa2eb",
        "searchCriteria.conservationArea": "CA25",
        "caseAddressType": "Application",
        "date(applicationValidatedStart)": "27/04/2020",
        "date(applicationValidatedEnd)": "16/07/2020",
        "searchType": "Application"
    }

    ap_request = ApplicationRequest(params=request)
    ap_request.createSession()
    ap_request.searchRequest()

    # response_valid, response_message = ap_request.searchRequest()
    #
    # if response_valid:
    #     print(response_message)
    # # If the http response is not valid: return
    # else:
    #     print(response_message)
    #     return

    # number_applications = ap_request.extractShowingInt()
    # print(f"Search found {number_applications} applications...")

    #
    # # STEP 3
    # progress_per_page = int(65 // ap_request.pages - 1)
    # progress = 25
    #
    # with concurrent.futures.ThreadPoolExecutor() as executor:
    #     futures = [executor.submit(ap_request.nextPage, i) for i in range(2, ap_request.pages + 1)]
    #     print("[LOG] Request threads started")
    #     for i, _ in enumerate(concurrent.futures.as_completed(futures)):
    #         print(f"Searching page {i + 2}")
    #     # concurrent.futures.wait(futures, return_when="ALL_COMPLETED")
    #     print("[LOG] Request threads finished")
    #
    # # EXTRACT DATA
    # ap_request.ExtractData()
    # print("Data extracted...")
    # print(ap_request.all_applications)


if __name__ == '__main__':
    Test()
