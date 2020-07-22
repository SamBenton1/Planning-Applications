# Planning Applications Search
###Introduction
The planning application search tool is a PyQt5 based GUI that allows the user to compile results
from a search done through the GUI into a spread sheet for the data to be easily accessible. The search application
can get result from two websites. The Poole planning applications website and the East Dorset planning applications
website.

#### Methods
The application uses the python requests library the python web scrapping library BeautifulSoup to do the majority
of the work. The results for web searches are retrieved by web scrapping and are then stored in objects which are they processed
by regular expressions to get rid of unwanted listings.

