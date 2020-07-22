from github import Github
import time
import pickle

# Gets the token from the bin file
with open("resources/token.bin", "rb") as config:
    TOKEN = pickle.load(config)["TOKEN"]


# Returns string formatted time
def clock():
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime())


# LOG ERROR
def Log(error_message, request=""):
    """
    Writes errors to log file for inspection if the app crashes

    :param error_message: The message to be logged
    :param request: The request that caused the error
    :return: None
    """
    print(f"[LOGGING] {error_message}")
    request_string = f"REQUEST = {request}" if request else ""
    with open("errors.log", "a") as error_logs:
        error_logs.write(f"[LOG] {clock()} :: {error_message} {request_string}\n")

# PRIVATE - Unused
def _LogIssue(title, request):
    """
    This function takes an issue and the request that caused it and sends it to
    my github issues page.

    :param title: The Issue
    :param request: The rquest that caused it
    :return: None
    """
    git = Github(TOKEN)
    repo = git.get_repo("SamBenton1/Planning-Applications")

    issue = repo.create_issue(
        title=title,
        body=f"""[ISSUE] {clock()}
        
        REQUEST = {request}
        """
    )
    print(issue)

