import time
import pickle


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

