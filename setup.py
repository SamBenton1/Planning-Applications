"""
This setup contains the script for building an executable using cx_freeze
"""
import sys
from cx_Freeze import setup, Executable

build_exe_options = {
    "includes": ["PyQt5"],
    "include_files": ["resources", "errors.log", "Spreadsheets"],
    "optimize": 1,
}

bdist_options = {
    "target_name": "Planning Application Search Installer",
    "install_icon": "resources/exe_icon.ico"
}

setup(
    name="Application Search",
    version="0.1",
    author="Sam Benton",
    description="Search tool to create spreadsheet of planning applications",
    options={"build_exe": build_exe_options,
             "bdist_msi": bdist_options},
    executables=[Executable("PooleGUi.py",
                            icon="resources/exe_icon.ico",
                            base="Win32GUI",
                            targetName="Planning Applications.exe",
                            ),
                 Executable("PooleGUi.py",
                            icon="resources/exe_icon.ico",
                            targetName="Debug.exe",
                            ),
                 ]
)
