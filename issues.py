from github import Github
import time
import pickle

with open("resources/config.bin", "rb") as config:
    TOKEN = pickle.load(config)["TOKEN"]


# Returns string formatted time
def clock():
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime())


# Log Errors
def Log(error_message, request=""):
    print(f"[LOGGING] {error_message}")
    request_string = f"REQUEST = {request}" if request else ""
    with open("errors.log", "a") as error_logs:
        error_logs.write(f"[LOG] {clock()} :: {error_message} {request_string}\n")


def LogHTML(response):
    with open("failed.html", "w") as error_file:
        print("writing error html")
        error_file.write(response.content.decode("utf-8"))


def LogIssue(title, request):
    return
    git = Github(TOKEN)
    repo = git.get_repo("SamBenton1/Planning-Applications")

    issue = repo.create_issue(
        title=title,
        body=f"""[ISSUE] {clock()}
        
        REQUEST = {request}
        """
    )
    print(issue)

