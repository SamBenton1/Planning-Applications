import sys
from cx_Freeze import setup, Executable

build_exe_options = {
    "includes": ["PyQt5"],
    "include_files": [
        r"resources",
        r"application_request.py",
        r"select_reference.py"
    ]
}

setup(
    name="Application Search",
    version="0.1",
    author="Sam Benton",
    description="Search tool to create spreadsheet of planning applications",
    options={"build_exe": build_exe_options},
    executables=[Executable("main.py",
                            icon="resources\exe_icon.ico",
                            base="Win32GUI",
                            targetName="Planning Applications.exe",
                            )]
)